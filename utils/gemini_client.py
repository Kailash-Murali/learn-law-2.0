import os
from typing import List, Optional, AsyncGenerator
from dotenv import load_dotenv
from google import genai

class GeminiClient:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize the Gemini API with your API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not found")
        
        # Initialize the client
        self.client = genai.Client(api_key=api_key)
        
        # Set default parameters
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        # Model name
        self.model_name = "gemini-2.5-flash"

    def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text using Gemini Pro model.
        
        Args:
            prompt (str): The input prompt for generation
            temperature (float, optional): Controls randomness in generation
            max_tokens (int, optional): Maximum number of tokens to generate
            
        Returns:
            str: Generated text response
        """
        # Create a custom config if parameters are provided
        generation_config = self.generation_config.copy()
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["max_output_tokens"] = max_tokens

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return ""

    async def generate_text_stream(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text using Gemini Pro model with streaming response.
        
        Args:
            prompt (str): The input prompt for generation
            temperature (float, optional): Controls randomness in generation
            max_tokens (int, optional): Maximum number of tokens to generate
            
        Returns:
            AsyncGenerator: Stream of generated text chunks
        """
        generation_config = self.generation_config.copy()
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["max_output_tokens"] = max_tokens

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                generation_config=generation_config,
                stream=True
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"Error generating content stream: {str(e)}")
            yield ""

    def chat(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Have a chat conversation using Gemini Pro model.
        
        Args:
            messages (List[dict]): List of message dictionaries with 'role' and 'content'
            temperature (float, optional): Controls randomness in generation
            max_tokens (int, optional): Maximum number of tokens to generate
            
        Returns:
            str: Generated response
        """
        generation_config = self.generation_config.copy()
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["max_output_tokens"] = max_tokens

        try:
            # Format messages for the new API
            formatted_messages = []
            for message in messages:
                formatted_messages.append({
                    "role": message["role"],
                    "parts": [{"text": message["content"]}]
                })
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=formatted_messages,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return ""


# Example usage
if __name__ == "__main__":
    # Initialize the client
    client = GeminiClient()
    
    # Example of simple text generation
    response = client.generate_text(
        "Explain the concept of quantum computing in simple terms.",
        temperature=0.8
    )
    print("Text Generation Response:", response)
    
    # Example of chat
    messages = [
        {"role": "user", "content": "What is artificial intelligence?"},
        {"role": "assistant", "content": "Artificial Intelligence (AI) is..."},
        {"role": "user", "content": "Can you give me some examples of AI applications?"}
    ]
    
    chat_response = client.chat(messages, temperature=0.7)
    print("\nChat Response:", chat_response)