## Autorius   
Projektą sukūrė *Justas Kaulakis*.  
Grupė: *IFB-3*  
*KTU Informatikos inžinerija. 2026 m.*  
Repo: https://github.com/Justas-Kaulakis/steg-app

<img width="811" height="610" alt="image" src="https://github.com/user-attachments/assets/f9b00795-66c5-4b16-884e-25b0e484310e" />


## Programos aprašymas 
Ši programa skirta pademonstruoti skaitmeninių vandens ženklų ir steganografijos veikimą naudojant paveikslėlius. Programa leidžia uždėti matomą vandens ženklą ant paveikslėlio, paslėpti tekstinį pranešimą naudojant LSB metodą, išgauti paslėptą tekstą bei palyginti paveikslėlio metaduomenis prieš ir po ženklinimo. 
## Programavimo kalba ir aplinka 
Programavimo kalba: Python.  
Grafinė vartotojo sąsaja: PySide6 (Qt for Python) biblioteka. 
## Naudotos bibliotekos 
-	PySide6 – grafinės vartotojo sąsajos kūrimui (langai, mygtukai, skirtukai, teksto laukai, paveikslėlių peržiūra).  
-	Pillow (PIL) – paveikslėlių nuskaitymui, apdorojimui, vandens ženklo uždėjimui ir išsaugojimui. 
## Pasirinkti ženklinimo metodai 
1. Matomas vandens ženklas 
Matomam vandens ženklinimui naudojamas paveikslėlio uždėjimo ant kito paveikslėlio metodas. Naudotojas gali pasirinkti pagrindinį paveikslėlį, pasirinkti vandens ženklo paveikslėlį, nustatyti pasvirimo kampą, mastelį, permatomumą, poziciją bei pasirinkti, ar vandens ženklas bus kartojamas visame paveikslėlyje. 
2. Nematomas vandens ženklas / steganografija (LSB)   
Programoje tekstinis pranešimas pirmiausia paverčiamas baitais, tada šie baitai suskaidomi į bitus. Toliau tie bitai įrašomi į paveikslėlio RGB kanalų mažiausiai reikšmingus bitus. Išgavimo metu atliekamas atvirkštinis procesas – nuskaitomi mažiausiai reikšmingi bitai, atkuriami baitai ir galiausiai atkuriamas tekstinis pranešimas. 
 
## Programos funkcijos 
-	Matomo vandens ženklo uždėjimas ant paveikslėlio. 
-	Tekstinio pranešimo slėpimas paveikslėlyje naudojant LSB metodą. 
-	Paslėpto tekstinio pranešimo išgavimas. 
-	Paveikslėlio „išvalymas“ nuo LSB pranešimo. 
-	Paveikslėlių metaduomenų peržiūra prieš ir po ženklinimo. 
## Programos paleidimas:
1. Įdiegti Python 3.10 arba naujesnė versija
2. Sukurti ir aktyvuoti virtualią aplinką (venv)
   Projekto kataloge terminale sukurkite virtualią aplinką: python -m venv .venv.
   Tada ją aktyvuokite (tai skriptas): .venv\Scripts\activate
4. Įdiegti reikalingas bibliotekas: pip install -r requirements.txt
5. Paleisti programą:  python main.py
## Kaip naudotis programa  
1. Pasirinkti norimą skirtuką: matomas vandens ženklas arba LSB steganografija. 
2. Įkelti paveikslėlį naudojant mygtuką Load image arba Load base image. 
3. Matomo vandens ženklo atveju pasirinkti papildomą vandens ženklo paveikslėlį ir nustatyti parametrus. 
4. LSB atveju įvesti tekstą ir paspausti Encode text. 
5. Norint atkurti tekstą, naudoti Extract text. 
6. Norint pašalinti paslėptą pranešimą, naudoti Clean image. 
7. Galutinį rezultatą išsaugoti naudojant Save image. 
