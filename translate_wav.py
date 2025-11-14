import os
import sys
import argparse
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime
 
def translate_wav(
    wav_path: str,
    target_language: str,
    source_language: str | None = None,
    output_txt: str | None = None
):
    """
    Translate speech from a WAV file into text in the target language.
    - wav_path: path to .wav file
    - target_language: BCP-47 like 'en', 'hi', 'mr', 'fr', 'de', 'es', 'ja', etc.
    - source_language: set e.g. 'en-US'; if None, auto-detects among common languages
    - output_txt: save the translated text to a file if provided
    """
 
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        raise RuntimeError("Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables.")
 
    if not os.path.isfile(wav_path):
        raise FileNotFoundError(f"WAV file not found: {wav_path}")
 
    # 1) Create translation config
    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=speech_key,
        region=speech_region,
    )
 
    # You can set a specific source language, or auto-detect
    if source_language:
        translation_config.speech_recognition_language = source_language
    else:
        # Auto-detect source language among a list (add/remove as you wish)
        # If you know your likely source, prefer setting speech_recognition_language for best accuracy.
        auto_langs = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=["en-US", "hi-IN", "mr-IN", "gu-IN", "ta-IN", "te-IN", "bn-IN"]
        )
 
    # Add the desired target language (e.g., 'hi' for Hindi, 'mr' for Marathi, 'en' for English)
    translation_config.add_target_language(target_language)
 
    # 2) Audio input from WAV
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
 
    # 3) Create recognizer
    if source_language:
        recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=translation_config,
            audio_config=audio_config
        )
    else:
        recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=translation_config,
            audio_config=audio_config,
            auto_detect_source_language_config=auto_langs
        )
 
    # Collect results
    translated_lines = []
    recognized_lines = []  # (optional) source-language transcripts
    done = False
 
    def handle_recognizing(evt: speechsdk.SessionEventArgs):
        # Live partials available via evt.result
        pass  # you can print partials if you want
 
    def handle_recognized(evt: speechsdk.SessionEventArgs):
        result = evt.result
        if result.reason == speechsdk.ResultReason.TranslatedSpeech:
            src_text = result.text or ""
            # result.translations is a dict keyed by target language codes
            tgt_text = result.translations.get(target_language, "")
            if tgt_text:
                recognized_lines.append(src_text)
                translated_lines.append(tgt_text)
                # Print each finalized segment
                print(f"[SRC] {src_text}")
                print(f"[{target_language.upper()}] {tgt_text}\n")
        elif result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # Recognized but no translation (shouldn’t happen in TranslationRecognizer, but just in case)
            if result.text:
                print(f"[SRC only] {result.text}\n")
        elif result.reason == speechsdk.ResultReason.NoMatch:
            pass
 
    def handle_canceled(evt: speechsdk.SessionEventArgs):
        nonlocal done
        print(f"Canceled: {evt.reason}")
        if evt.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {evt.error_details}")
        done = True
 
    def handle_session_stopped(evt: speechsdk.SessionEventArgs):
        nonlocal done
        done = True
 
    recognizer.recognizing.connect(handle_recognizing)
    recognizer.recognized.connect(handle_recognized)
    recognizer.canceled.connect(handle_canceled)
    recognizer.session_stopped.connect(handle_session_stopped)
 
    print("Starting translation...")
    recognizer.start_continuous_recognition()
    while not done:
        # simple loop; SDK runs callbacks on background threads
        pass
    recognizer.stop_continuous_recognition()
 
    # Save to file if requested
    if output_txt:
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(translated_lines))
        print(f"\nSaved translated text → {output_txt}")
 
    return translated_lines, recognized_lines
 
def main():
    parser = argparse.ArgumentParser(description="Translate a WAV file using Azure Speech Translation.")
    parser.add_argument("wav", help="Path to .wav file")
    parser.add_argument("--to", required=True, help="Target language (e.g., en, hi, mr, fr, de, es)")
    parser.add_argument("--from-lang", default=None, help="Source language (e.g., en-US). If omitted, auto-detect.")
    parser.add_argument("--out", default=None, help="Optional path to save translated text")
    args = parser.parse_args()
 
    translate_wav(
        wav_path=args.wav,
        target_language=args.to,
        source_language=args.from_lang,
        output_txt=args.out
    )
 
if name == "main":
    main()
