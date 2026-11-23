
# import asyncio
# import tempfile
# from pathlib import Path

# import edge_tts
# from playsound3 import playsound


# class TTSEngine:

#     def __init__(
#         self,
#         voice="vi-VN-HoaiMyNeural",
#         rate="+5%",
#         pitch="+15Hz",
#         volume="+0%"
#     ):
#         self.voice = voice
#         self.rate = rate
#         self.pitch = pitch
#         self.volume = volume

#     async def _generate_audio(self, text, output_path):

#         communicate = edge_tts.Communicate(
#             text=text,
#             voice=self.voice,
#             rate=self.rate,
#             pitch=self.pitch,
#             volume=self.volume
#         )

#         await communicate.save(output_path)

#     def speak(self, text):

#         if not text or not text.strip():
#             return

#         temp_path = None

#         try:
#             with tempfile.NamedTemporaryFile(
#                 suffix=".mp3",
#                 delete=False
#             ) as temp_file:
#                 temp_path = temp_file.name

#             asyncio.run(
#                 self._generate_audio(text, temp_path)
#             )

#             audio_file = Path(temp_path)

#             if not audio_file.exists() or audio_file.stat().st_size == 0:
#                 raise RuntimeError("TTS generated an empty audio file!")

#             playsound(str(audio_file))

#         except Exception as error:
#             print(f"\n[VOICE ERROR] {type(error).__name__}: {error}")

#         finally:
#             if temp_path:
#                 Path(temp_path).unlink(missing_ok=True)
