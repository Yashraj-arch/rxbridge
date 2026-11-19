from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models.medicine import CustomMedicine

STANDARD_MEDICINES: List[Dict[str, str]] = [
    {"name": "Dolo 650", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Dolo 500", "dose": "1 tab BD", "duration": "3 days"},
    {"name": "Crocin 500", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Crocin Advance", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Combiflam", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Meftal Spas", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Meftal P", "dose": "1 tab BD", "duration": "3 days"},
    {"name": "Ibugesic Plus", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Brufen 400", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Voveran 50", "dose": "1 tab BD", "duration": "5 days"},
    {"name": "Voveran SR 100", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Diclofenac 50mg", "dose": "1 tab BD", "duration": "5 days"},
    {"name": "Nimesulide 100mg", "dose": "1 tab BD", "duration": "3 days"},
    {"name": "Nise 100", "dose": "1 tab BD", "duration": "3 days"},
    {"name": "Etoshine 90", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Augmentin 625", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Augmentin 1g", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Amoxicillin 500mg", "dose": "1 cap TDS", "duration": "7 days"},
    {"name": "Mox 500", "dose": "1 cap TDS", "duration": "7 days"},
    {"name": "Azithral 500", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Azee 500", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Zithromax 500", "dose": "1 tab OD", "duration": "3 days"},
    {"name": "Cifran 500", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Ciplox 500", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Norflox 400", "dose": "1 tab BD", "duration": "5 days"},
    {"name": "Oflox 200", "dose": "1 tab BD", "duration": "5 days"},
    {"name": "Taxim O 200", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Cefixime 200", "dose": "1 tab BD", "duration": "7 days"},
    {"name": "Monocef 1g", "dose": "1g IV OD", "duration": "7 days"},
    {"name": "Doxycycline 100", "dose": "1 cap BD", "duration": "7 days"},
    {"name": "Metronidazole 400", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Flagyl 400", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Tinidazole 500", "dose": "2 tab OD", "duration": "3 days"},
    {"name": "Pantop 40", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Pan 40", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Pan D", "dose": "1 cap OD", "duration": "14 days"},
    {"name": "Omez 20", "dose": "1 cap OD", "duration": "14 days"},
    {"name": "Omez D", "dose": "1 cap OD", "duration": "14 days"},
    {"name": "Rablet 20", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Razo 20", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Nexpro 40", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Nexium 40", "dose": "1 tab OD", "duration": "14 days"},
    {"name": "Gelusil", "dose": "2 tsp after meals", "duration": "7 days"},
    {"name": "Cetirizine 10", "dose": "1 tab HS", "duration": "5 days"},
    {"name": "Cetzine", "dose": "1 tab HS", "duration": "5 days"},
    {"name": "Allegra 120", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Allegra 180", "dose": "1 tab OD", "duration": "5 days"},
    {"name": "Montair LC", "dose": "1 tab HS", "duration": "10 days"},
    {"name": "Montek LC", "dose": "1 tab HS", "duration": "10 days"},
    {"name": "Avil 25", "dose": "1 tab SOS", "duration": "3 days"},
    {"name": "Ascoril D", "dose": "2 tsp TDS", "duration": "5 days"},
    {"name": "Ascoril LS", "dose": "2 tsp TDS", "duration": "5 days"},
    {"name": "Benadryl", "dose": "2 tsp TDS", "duration": "5 days"},
    {"name": "Alex Syrup", "dose": "2 tsp TDS", "duration": "5 days"},
    {"name": "Grilinctus", "dose": "2 tsp TDS", "duration": "5 days"},
    {"name": "Asthalin 2mg", "dose": "1 tab TDS", "duration": "5 days"},
    {"name": "Deriphyllin", "dose": "1 tab BD", "duration": "5 days"},
    {"name": "Glycomet 500", "dose": "1 tab BD", "duration": "30 days"},
    {"name": "Glycomet GP 1", "dose": "1 tab BD", "duration": "30 days"},
    {"name": "Telma 40", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Telma AM", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Amlong 5", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Shelcal 500", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Becosules", "dose": "1 cap OD", "duration": "15 days"},
    {"name": "Neurobion Forte", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Limcee 500", "dose": "1 tab OD", "duration": "15 days"},
    {"name": "Zincovit", "dose": "1 tab OD", "duration": "30 days"},
    {"name": "Liv 52", "dose": "2 tab BD", "duration": "30 days"},
    {"name": "Cremaffin", "dose": "2 tsp HS", "duration": "5 days"},
    {"name": "Dulcolax 5", "dose": "1-2 tab HS", "duration": "3 days"},
    {"name": "Eldoper", "dose": "1 cap SOS", "duration": "2 days"},
    {"name": "Econorm", "dose": "1 sachet BD", "duration": "3 days"},
    {"name": "Electral", "dose": "1 sachet in 1L water", "duration": "3 days"},
    {"name": "Ondem 4", "dose": "1 tab SOS", "duration": "3 days"},
    {"name": "Emset 4", "dose": "1 tab SOS", "duration": "3 days"},
    {"name": "Domstal 10", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Cyclopam", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Buscopan 10", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Stugeron 25", "dose": "1 tab TDS", "duration": "3 days"},
    {"name": "Vertin 16", "dose": "1 tab TDS", "duration": "7 days"},
]

def search_medicines(db: Session, query: str, limit: int = 8) -> List[Dict[str, str]]:
    q = query.strip().lower()
    results: List[Dict[str, str]] = []
    seen = set()

    # Search standard
    for med in STANDARD_MEDICINES:
        if q in med["name"].lower():
            if med["name"].lower() not in seen:
                results.append(med)
                seen.add(med["name"].lower())
            if len(results) >= limit:
                return results

    # Search custom
    custom_records = db.query(CustomMedicine).filter(CustomMedicine.name.ilike(f"%{q}%")).limit(limit).all()
    for cm in custom_records:
        if cm.name.lower() not in seen:
            results.append({
                "name": cm.name,
                "dose": cm.dose or "",
                "duration": cm.duration or ""
            })
            seen.add(cm.name.lower())
        if len(results) >= limit:
            break

    return results

def get_all_medicines(db: Session) -> List[Dict[str, str]]:
    all_meds = list(STANDARD_MEDICINES)
    seen = {m["name"].lower() for m in all_meds}
    customs = db.query(CustomMedicine).all()
    for cm in customs:
        if cm.name.lower() not in seen:
            all_meds.append({
                "name": cm.name,
                "dose": cm.dose or "",
                "duration": cm.duration or ""
            })
            seen.add(cm.name.lower())
    return all_meds
