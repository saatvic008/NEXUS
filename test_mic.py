"""Quick mic test — just list mics and try to capture audio."""
import speech_recognition as sr

r = sr.Recognizer()
r.dynamic_energy_threshold = True

# List mics
print("Available microphones:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"  [{i}] {name}")

# Try with default mic
print("\nCalibrating default mic (2 sec)... be quiet.")
mic = sr.Microphone()
with mic as source:
    r.adjust_for_ambient_noise(source, duration=2)
print(f"Threshold: {r.energy_threshold:.0f}")

print("\nSay something NOW (you have 5 seconds)...")
with mic as source:
    audio = r.listen(source, phrase_time_limit=5)
print("Audio captured! Recognizing...")

try:
    text = r.recognize_google(audio)
    print(f"SUCCESS - Google heard: '{text}'")
except sr.UnknownValueError:
    print("FAIL - Google could not understand audio (mic may be too quiet)")
except sr.RequestError as e:
    print(f"FAIL - No internet or Google API error: {e}")
