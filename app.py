from io import BytesIO
from typing import Optional, Dict
import os
import chainlit as cl
import google.generativeai as genai
from chainlit.element import ElementBased
from groq import Groq
from pyht import Client
from pyht.client import TTSOptions

# Hard-code your OAuth credentials
CLIENT_ID = "676597742614-c6tres4rbk0tkvnh6g8fnictlbg9ctd3.apps.googleusercontent.com"  
CLIENT_SECRET = "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"  

# Initialize OAuth with hard-coded credentials
cl.oauth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Initialize the Groq client
client = Groq(api_key="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")

@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    user_name = raw_user_data.get('name', 'there')  
    cl.user_session.set('user_name', user_name) 
    return default_user

async def speech_to_text(audio_file):
    response = client.audio.translations.create(
        file=audio_file, 
        model="whisper-large-v3",  
        prompt="Specify context or spelling", 
        response_format="json", 
        temperature=0.0  
    )
    return response.text

def text_to_speech(text):
    client = Client(
        user_id="4PITN4xNgkQvptZ1JKpoMqPAozB2",
        api_key="15667a819f71438f88c2027d6b4ebb8f",
    )

    # Text-to-Speech options
    options = TTSOptions(voice="s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jennifersaad/manifest.json")

    # Open a file to store the output audio
    with open("output_audio.mp3", "wb") as audio_file:
        for chunk in client.tts(text, options):
            audio_file.write(chunk)

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    if chunk.isStart:
        buffer = BytesIO()
        buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}"
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("audio_mime_type", chunk.mimeType)

    cl.user_session.get("audio_buffer").write(chunk.data)

@cl.on_audio_end
async def on_audio_end(elements: list[ElementBased]):
    audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
    audio_buffer.seek(0)
    transcription = await speech_to_text(audio_buffer)
    await cl.Message(content=transcription).send()

    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(transcription)
    text_to_speech(response.text)
    elements = [
        cl.Audio(path="output_audio.mp3", display="inline", auto_play=True),
    ]
    await cl.Message(
        content="Question",
        elements=elements,
    ).send()

@cl.on_message
async def stop_message(message: str):
    if message.content == "":
        pass
    else:
        await cl.Message(content="Please give input through voice").send()

# Send personalized greeting after OAuth login
@cl.on_chat_start
async def greet_user():
    user_name = cl.user_session.get('user_name', 'there')
    greeting = f"Hello {user_name}, I'm your virtual assistant! How can I assist you today?"
    await cl.Message(content=greeting).send()

@cl.on_message
async def handle_message(message):
    if message.content.startswith("oauth:"):
        user_name = message.content.split(":")[1]  
        try:
            cl.user_session.set('user_name', user_name)
        except cl.ChainlitContextException:
            print("Chainlit context is not available.")

# Run the Chainlit application
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))  
    cl.run(app=cl, host="0.0.0.0", port=port)  
