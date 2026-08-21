import google.generativeai as genai

# IMPORTANT: Paste your actual API key here!
genai.configure(api_key="AQ.Ab8RN6JvgsN4TsaBmJaL8Qxv5EvAdSPrz-XXgCwRAZE6np4Qsg")

print("Checking available models for your API key...")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)