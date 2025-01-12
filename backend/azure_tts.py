# backend/azure_tts.py
import os
import azure.cognitiveservices.speech as speechsdk
from pydantic_settings import BaseSettings, SettingsConfigDict

class TTSSettings(BaseSettings):
    azure_speech_key: str
    azure_speech_region: str

    # This tells Pydantic Settings to load environment variables from .env
    model_config = SettingsConfigDict(env_file=".env",  extra="allow" )

def generate_speech(text: str) -> bytes:
    """
    Generate TTS audio bytes from Azure Speech.
    Returns WAV or MP3 audio data (depending on config).
    """
    # 1) Load env from .env
    settings = TTSSettings()  
    speech_key = settings.azure_speech_key
    speech_region = settings.azure_speech_region

    # 2) Set up Azure Speech
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    # 3) Return audio bytes if successful
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    else:
        print(f"Speech synthesis failed with reason: {result.reason}")
        return b""