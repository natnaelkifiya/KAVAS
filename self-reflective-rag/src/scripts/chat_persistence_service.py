import json, os, re
from dotenv import load_dotenv, find_dotenv
from pymongo import MongoClient
from openai import OpenAI
from datetime import datetime

# Load environment variables
load_dotenv(find_dotenv())

class ChatHistory:
    MAX_TOKEN_COUNT = 300
    LAST_MESSAGES_TO_KEEP = 3

    def __init__(self, mongo_host:str, mongo_port:str, mongo_user:str, mongo_pass:str, openai_key:str, openai_model:str, auth_source:str = "admin", auth_mechanism:str = "SCRAM-SHA-1"):
        # initialize the mongo client
        self.connection_uri = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/?authSource={auth_source}&authMechanism={auth_mechanism}"
        self.client = MongoClient(self.connection_uri)
        print('Mongo connection string: ', self.connection_uri)
        
        # obtain the KAVAS database 
        self.db = self.client["KAVAS"]
                
        # create collections if not present
        existing_collection = self.db.list_collection_names()
        if "chat-history" not in existing_collection:
            self.db.create_collection("chat-history")
            print("Created the chat-hisotry collection")
            self.chat_collection = self.db["chat-history"]
        else:
            self.chat_collection = self.db["chat-history"]

        # initialize an ai client
        self.ai_client = OpenAI(api_key=openai_key)
        self.ai_model = openai_model


    @staticmethod
    def get_token_count(messages):
        """
        Calculate the token count of messages.
        """
        total_token_count = 0
        for msg in messages:
            user_message = msg.get("user_message", "")  # Default to empty string if missing
            ai_message = msg.get("ai_message", "")

            if isinstance(user_message, str) and isinstance(ai_message, str):
                total_token_count += len(user_message.split()) + len(ai_message.split())
        print(total_token_count)
        return total_token_count
    
    def get_chat_history(self, user_id):
        """
        Retrieve conversation history with guaranteed structure
        """
        user_chat = self.chat_collection.find_one({"user_id": user_id})
        if not user_chat:
            return None
        
        # Initialize response with all possible fields
        response = {
            "user_details": user_chat.get("user_details", {}),
            "summary": user_chat.get("conversation_summary", "No summary available"),
            "recent_messages": user_chat.get("recent_messages", []),
            "full_history": user_chat.get("conversation_history", []),
            "type": "condensed" if "conversation_summary" in user_chat else "full"
        }
        
        return response
    
    def get_user_details(self, user_id):
        """
        Directly fetch stored user details.
        Args:
            user_id: User to look up
        Returns:
            dict: {'name': str, 'job': str} (partial if some info missing)
        """
        doc = self.chat_collection.find_one(
            {"user_id": user_id},
            {"user_details": 1}
        )
        return doc.get("user_details", {}) if doc else {}

    def save_chat_message(self, user_id, user_message, ai_message):
        """With enhanced type safety"""
        timestamp = datetime.utcnow().isoformat()
        
        # Ensure messages are strings
        user_message = str(user_message)[:2000]
        ai_message = str(ai_message.get('generation', ai_message) if isinstance(ai_message, dict) else str(ai_message))
        ai_message = ai_message[:2000]
        
        new_message = {
            'user_message': user_message,
            'ai_message': ai_message,
            'timestamp': timestamp
        }

        # Rest of your save logic remains the same...

        user_chat = self.chat_collection.find_one({'user_id': user_id})
        
        if user_chat:
            # Get all existing messages
            all_messages = user_chat.get('conversation_history', [])
            if 'recent_messages' in user_chat:
                all_messages.extend(user_chat['recent_messages'])
            
            # Add new message
            all_messages.append(new_message)
            
            # Calculate tokens
            total_tokens = ChatHistory.get_token_count(all_messages)
            print(f"Total tokens: {total_tokens} (Threshold: {ChatHistory.MAX_TOKEN_COUNT})")
            
            if total_tokens > ChatHistory.MAX_TOKEN_COUNT:
                # Summarize all except last N messages
                to_summarize = all_messages[:-ChatHistory.LAST_MESSAGES_TO_KEEP]
                recent_messages = all_messages[-ChatHistory.LAST_MESSAGES_TO_KEEP:]
                
                # Truncate recent messages before storing
                truncated_recent_messages = []
                for msg in recent_messages:
                    truncated_msg = {
                        'user_message': msg['user_message'][:500],  # Truncate to 500 chars
                        'ai_message': msg['ai_message'][:500],
                        'timestamp': msg['timestamp']
                    }
                    truncated_recent_messages.append(truncated_msg)
                
                summary = self.summarize_conversation(to_summarize)
                user_details = self.extract_user_details(all_messages)
                
                # Update database with truncated recent messages
                self.chat_collection.update_one(
                    {'user_id': user_id},
                    {'$set': {
                        'conversation_summary': summary,
                        'recent_messages': truncated_recent_messages,
                        'user_details': user_details,
                        'last_updated': timestamp
                    }, '$unset': {'conversation_history': ""}},
                    upsert=True
                )
            else:
                # Update normally
                self.chat_collection.update_one(
                    {'user_id': user_id},
                    {'$set': {
                        'conversation_history': all_messages,
                        'last_updated': timestamp
                    }},
                    upsert=True
                )
        else:
            # New user
            self.chat_collection.insert_one({
                'user_id': user_id,
                'conversation_history': [new_message],
                'created_at': timestamp,
                'last_updated': timestamp
            })

    def extract_details_via_llm(self, recent_messages):
        """
        Fallback LLM extraction when pattern matching fails.
        Args:
            recent_messages: List of the last 5 message dicts
        Returns:
            str: Formatted "Name: X; Job: Y" or empty string
        """
        print('Extracting details via LLM')
        conversation = "\n".join(msg.get("user_message", "") for msg in recent_messages)
        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{
                    "role": "system",
                    "content": "Extract ONLY: 1) Full name, 2) Job title. Return as 'Name: X; Job: Y' or ''"
                }, {
                    "role": "user",
                    "content": conversation
                }],
                temperature=0,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return ""
    
    def extract_user_details(self, messages):
        """
        Extract name and job using regex patterns with LLM fallback.
        Improved to prevent duplicate values and better pattern matching.
        Args:
            messages: List of message dicts
        Returns:
            dict: {'name': str, 'job': str} (missing keys if not found)
        """
        print('Extracting user details')
        patterns = {
            "name": [
                r"(?:my name is|i'm called|call me) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
                r"(?:i am|name's) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)"
            ],
            "job": [
                r"(?:i work as|my job is) (?:a )?([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
                r"(?:i'm|i am) (?:a )?([A-Z][a-z]+(?: [A-Z][a-z]+)*)(?: engineer| developer| analyst)?"
            ]
        }
        
        details = {}
        
        for msg in messages:
            text = msg.get("user_message", "").strip()
            if not text:
                continue
                
            # Case-sensitive matching for proper nouns
            if "name" not in details:
                for pattern in patterns["name"]:
                    if match := re.search(pattern, text):
                        details["name"] = match.group(1)
                        break
                        
            if "job" not in details:
                for pattern in patterns["job"]:
                    if match := re.search(pattern, text):
                        # Additional validation to prevent name being captured as job
                        job = match.group(1)
                        if "name" in details and job == details["name"]:
                            continue
                        details["job"] = job
                        break
        
        # LLM fallback with duplicate prevention
        if (not details or 
            ("name" in details and "job" in details and details["name"] == details["job"])):
            if llm_result := self.extract_details_via_llm(messages[-5:]):
                if "Name:" in llm_result and "Job:" in llm_result:
                    name = llm_result.split("Name:")[-1].split(";")[0].strip()
                    job = llm_result.split("Job:")[-1].strip()
                    if name != job:  # Only use if they're different
                        details.update({"name": name, "job": job})
        
        # Final validation
        if "name" in details and "job" in details and details["name"] == details["job"]:
            del details["job"]  # Remove duplicate value
        print(details)
        return details

    def summarize_conversation(self, messages):
        """
        Robust summarization with proper type checking
        """
        if not messages:
            return "No messages to summarize", []
        
        # Process messages with type safety
        processed_messages = []
        for msg in messages:
            # Ensure messages are strings
            user_msg = str(msg.get('user_message', ''))
            ai_msg = str(msg.get('ai_message', ''))
            
            # Split into sentences if they exist
            user_chunks = [s.strip() for s in re.split(r'(?<=[.!?]) +', user_msg) if s] if user_msg else []
            ai_chunks = [s.strip() for s in re.split(r'(?<=[.!?]) +', ai_msg) if s] if ai_msg else []
            
            # Rebuild into chunks
            max_chunk_length = 3
            for i in range(0, max(len(user_chunks), len(ai_chunks)), max_chunk_length):
                chunk = {
                    'user_message': ' '.join(user_chunks[i:i+max_chunk_length]),
                    'ai_message': ' '.join(ai_chunks[i:i+max_chunk_length]),
                    'timestamp': msg.get('timestamp')
                }
                processed_messages.append(chunk)
        
        try:
            # Generate summary
            conversation_text = "\n".join(
                f"User: {msg['user_message']}\nAI: {msg['ai_message']}" 
                for msg in processed_messages
            )[:8000]  # Stay within context limits
            
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{
                    "role": "system",
                    "content": "Summarize this conversation concisely:"
                }, {
                    "role": "user",
                    "content": conversation_text
                }],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content.strip(), messages[-ChatHistory.LAST_MESSAGES_TO_KEEP:]
        except Exception as e:
            print(f"Summarization error: {e}")
            return "Conversation summary unavailable", messages[-ChatHistory.LAST_MESSAGES_TO_KEEP:]

    def greet_user(self, user_id):
        # obtain the history
        history = self.get_chat_history(user_id=user_id)

        # get the current time
        time = datetime.now()
        hour = time.hour

        # simple prompt for greeting 
        greeting_prompt = [
            {"role": "system",
             "content": "You are KAVAS, the AI assistant at Kifiya Technologies. You can answer any question about the company and what it does. Your purpose it to greet people provided their chat history. Look for their names and greet them accordingly. If you can't find their name still greet them but also introduce yourself and tell them what you can do and you know be a good receptionist.\n"
             "           You will get the chat_history, the time(datetime.datetime.now()) so you can determine whether to use evening or morning afternoon."},
             {"role": "user",
              "content": f"chat_history: {history} \n\n time: {hour}"}
        ]

        response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=greeting_prompt,
                temperature=0.2,
                max_tokens=200
            )

        return response.choices[0].message.content.strip()