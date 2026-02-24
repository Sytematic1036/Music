# Learnings - EXP-002 Music Test Organizer

## Vad fungerade

1. **Enum-baserad kategorisering** - Att använda Python Enum för alla kategorier (TempoCategory, GenreCategory, etc.) ger:
   - Typsäkerhet
   - Lätt att iterera över alla värden
   - Konsekvent namngivning

2. **Mappning av synonymer** - Att ha en dictionary som mappar varianter ("ambience" -> AMBIENT, "peaceful" -> CALM) gör systemet mer flexibelt

3. **Separera filsystem-logik från intern state** - `_get_next_test_number_from_fs()` + intern `_next_test_number` counter fungerar bra tillsammans

4. **Dataclass för testfiler** - `TestFileInfo` med properties (`prefix`, `full_name`) är renare än strängmanipulation

## Vad INTE fungerade

1. **Windows path-längd** - Filnamn >200 tecken fungerar inte på Windows pga 260-teckens begränsning på path. Lösning: begränsa testfall till rimliga längder.

2. **Windows rename()** - `Path.rename()` på Windows kräver att målfilen inte existerar (till skillnad från Unix). Lösning: ta bort målfilen först eller använd annan metod.

3. **Pytest samlar dataclasses** - Klasser som börjar med "Test" (som `TestFile`) försöker pytest samla som test-klasser. Lösning: byt namn till `TestFileInfo` eller filtrera bort i conftest.py.

## Tekniska insikter

1. **Tempo-trösklar:**
   - Slow: < 80 BPM
   - Medium: 80-120 BPM
   - Fast: > 120 BPM

   Dessa värden är rimliga för avslappningsmusik men kan behöva justeras för andra genrer.

2. **Filkopiering vs flyttning** - Default är `copy=True` för att bevara originalfiler. Detta är säkrare men tar mer disk-utrymme.

3. **Metadata-cache** - Att cacha metadata i minnet (`_metadata_cache`) med möjlighet att spara/ladda från JSON gör systemet snabbt men kräver explicit save.
