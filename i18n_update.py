import os
import json

def update_translations(new_keys):
    lang_dir = "i18n"
    for file in os.listdir(lang_dir):
        if not file.endswith(".json"):
            continue
        path = os.path.join(lang_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = False
        for key in new_keys:
            if key not in data:
                data[key] = key
                updated = True
        if updated:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ {file} mis à jour")

if __name__ == "__main__":
    keys = ["✅ Paiement confirmé", "❌ Paiement annulé", "Crédits", "Boutique", "Bienvenue", "👤 Mon Profil"]
    update_translations(keys)
