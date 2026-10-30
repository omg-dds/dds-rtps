# RTPS Discovery Sniffer a JUnit Discovery Report

Nástroj pro odposlech a hloubkovou analýzu počátečního RTPS Discovery provozu (**SPDP** a **SEDP**) ve formátu **ParameterList (CDR)** podle OMG DDS-RTPS specifikace. Generuje samostatný JUnit XML report `junit_discovery_report_<timestamp>.xml` a strukturovaný JSON report `discovery_report_<timestamp>.json`.

---

## 1. Vytvořené a upravené soubory

- [`rtps_discovery_sniffer.py`](rtps_discovery_sniffer.py): Samostatný Python skript využívající `tshark` pro zachycení a dissekci RTPS discovery metatrafficu (SPDP na multicast portu 7400 a unicast/multicast SEDP).
- [`test_rtps_discovery_sniffer.py`](test_rtps_discovery_sniffer.py): Sada unit testů pokrývající dekódování parametrů, formátování časových značek, JUnit XML validaci a QoS kompatibilitu.
- [`Dockerfile`](Dockerfile): Doplněna instalace `tshark` s nastavením SUID práv (`chmod 4755 /usr/bin/dumpcap`) pro zachytávání síťových paketů v neprivilegovaném kontejneru.
- [`run_tests.sh`](run_tests.sh): Automatické spouštění discovery snifferu na pozadí během testování, podpora přepínačů `-d / --discovery-only`, `-t / --test` a `--skip-discovery`.
- [`run_tests_in_docker.sh`](run_tests_in_docker.sh): Předávání discovery parametrů, archivace discovery JSON reportů a spouštění kontejneru s `--cap-add=NET_ADMIN --cap-add=NET_RAW`.
- [`generate_reports.sh`](generate_reports.sh): Ošetřeno slučování JUnit XML reportů tak, aby discovery reporty zůstávaly oddělené od `junit_interoperability_report.xml`.
- [`.gitignore`](.gitignore): Doplněno ignorování generovaných discovery JSON reportů a dočasného souboru `timestamp`.

---

## 2. Extrahované parametry z Discovery

### SPDP (`DATA(p)` na portu 7400 / unicast metatraffic):
* **Vendor ID:** Dekódování hexadecimálního ID na čitelný název výrobce:
  - RTI Connext DDS (`01.01`)
  - Eclipse Cyclone DDS (`01.10`)
  - eProsima Fast DDS (`01.0f`)
  - OpenDDS (`01.03`)
  - Twin Oaks CoreDX DDS (`01.05`)
  - Dust DDS (`01.14`), RustDDS (`01.12`), GurumDDS (`01.11`) a další.
* **RTPS Protocol Version:** Extrakce verze protokolu (např. RTPS 2.1, 2.3, 2.4, 2.5).
* **Participant GUID Prefix:** 12bajtový unikátní identifikátor účastníka (24 hex znaků).
* **Locators:** IP adresy a porty (metatraffic i default data, unicast i multicast) s automatickým odstraněním duplicit.
* **Built-in Endpoints:** Dekódování bitové masky na jednotlivé discovery mechanismy (SEDP publication/subscription announcers/detectors, participant message datawriters/readers).
* **Lease Duration:** Časový limit platnosti účastníka v sekundách (Participant Lease Duration).

### SEDP (`DATA(w)` a `DATA(r)`):
* **Topic Name & Type Name:** Názvy témat a IDL datových typů (např. topic `Square`, type `ShapeType`).
* **Endpoint GUID & Entity Kind:** Rozlišení `DataWriter` (0x02, 0x03) vs `DataReader` (0x04, 0x07).
* **QoS profily:**
  - Reliability kind (`BEST_EFFORT` vs `RELIABLE`)
  - Durability kind (`VOLATILE`, `TRANSIENT_LOCAL`, `TRANSIENT`, `PERSISTENT`)
  - Ownership kind (`SHARED` vs `EXCLUSIVE`)
  - History depth
* **TypeInformation / TypeObject:** Detekce přítomnosti XTypes metadat.

---

## 3. Formát a struktura JUnit XML reportu

Soubor: **`junit_discovery_report_<timestamp>.xml`** (např. `junit_discovery_report_2026-09-22-18_54_00.xml`)

| TestCase | Účel | Podmínka selhání (Failure) |
|---|---|---|
| `Test_SPDP_Participant_Discovery` | Kontroluje detekci účastníků a jejich lokátorů | Počet účastníků `< expected_participants` |
| `Test_SPDP_Protocol_Version` | Ověřuje shodu s RTPS specifikací | Verze `< 2.1` nebo neplatný formát |
| `Test_SPDP_Vendor_Identification` | Identifikuje DDS stacky obou stran | Neznámé / nevalidní ID |
| `Test_SPDP_Builtin_Endpoints` | Kontroluje zapnutí discovery endpointů | Maska `0x00000000` |
| `Test_SEDP_Topic_Type_Match` | Ověřuje párování DataWriterů a DataReaderů | Neshoda v názvu tématu nebo typu (překlep v IDL) |
| `Test_SEDP_QoS_Compatibility` | Validuje pravidlo *Offered vs Requested* | Inkompatibilní QoS (např. Writer `BEST_EFFORT` vs Reader `RELIABLE`) |
| `Test_SEDP_Type_Information` | Reportuje přítomnost TypeObject / XTypes | Informativní test |

Každý testcase obsahuje v elementu `<system-out>` kompletní textový přehled discovery mapy, který vizualizují všechny standardní JUnit prohlížeče (např. `xunit-viewer` nebo GitHub Actions).

---

## 4. Použití v praxi

### A. Rychlý discovery test v Dockeru (~6 sekund):
Spustí pouze úvodní discovery test (`Test_Domain_0`) bez nutnosti čekat na všech 105 testů:
```bash
./run_tests_in_docker.sh \
    -p ./executables/connext_dds-7.7.0_shape_main_linux \
    -s ./executables/eclipse_cyclone-11.0.1_shape_main_linux \
    -d
```

### B. Kompletní testovací sada (interoperabilita + discovery):
Spustí celou sadu 105 interoperability testů a discovery sniffer automaticky zachytí počáteční discovery komunikaci:
```bash
./run_tests_in_docker.sh \
    -p ./executables/connext_dds-7.7.0_shape_main_linux \
    -s ./executables/eclipse_cyclone-11.0.1_shape_main_linux
```

### C. Samostatný odposlech z příkazové řádky:
```bash
# 1. Spustit discovery sniffer na pozadí (délka např. 5 sekund)
python3 rtps_discovery_sniffer.py -i any -d 5 &
SNIFFER_PID=$!

# 2. Spustit oba DDS účastníky
./executables/connext_dds-7.7.0_shape_main_linux -P -t Square -d 0 -b &
PUB_PID=$!
./executables/eclipse_cyclone-11.0.1_shape_main_linux -S -t Square -d 0 -b &
SUB_PID=$!

# 3. Počkat na dokončení snifferu
wait $SNIFFER_PID
```

### D. Analýza již existujícího PCAP souboru:
```bash
python3 rtps_discovery_sniffer.py -p /tmp/discovery_capture.pcap -t 20260922-19_02_32
```

### E. Zobrazení discovery reportu v HTML přes xunit-viewer:
```bash
npx -y xunit-viewer --results=./junit_discovery_report_20260922-19_02_32.xml --output=discovery_report.html
```

---

## 5. Integrace do Dockeru a testovacího skriptu

Skripty [`run_tests.sh`](run_tests.sh) i [`run_tests_in_docker.sh`](run_tests_in_docker.sh) podporují tyto parametry:

* **`-d` / `--discovery-only`**: Spustí pouze discovery test (`Test_Domain_0`) v délce cca 6 sekund.
* **`-t` / `--test <test_name>`**: Spustí jeden konkrétní test (např. `-t Test_Domain_0`).
* **`--skip-discovery`**: Přeskočí discovery sniffer a spustí pouze původní interoperability testy.
* **`--sniffer-duration <sec>`**: Určí délku odposlechu (výchozí: 15s pro celou sadu, 6s pro `-d`).

Vygenerované soubory po dokončení testu:
- `junit_discovery_report_<timestamp>.xml` (JUnit XML pro CI / test reporty)
- `discovery_report_<timestamp>.json` (strukturovaná data pro jq / automatizované validace)
- `junit_interoperability_report.xml` (sloučený interoperability report)
- `interoperability_report.xlsx` (Excel report)
- `index.html` (HTML vizualizace interoperability reportu)

Discovery reporty zůstávají oddělené a nejsou slučovány do `junit_interoperability_report.xml` díky filtru v `generate_reports.sh`.
