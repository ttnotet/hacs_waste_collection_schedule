import datetime
import requests
from waste_collection_schedule import Collection  # type: ignore[attr-defined]
from waste_collection_schedule.service.ICS import ICS


TITLE = "C-Trace.de"
DESCRIPTION = "Source for C-Trace.de."
URL = "https://c-trace.de/"
TEST_CASES = {"Bremen": {"ort": "Bremen", "strasse": "Abbentorstraße", "hausnummer": 5},
                "AugsburgLand": {"ort": "Königsbrunn", "strasse": "Marktplatz", "hausnummer": 7,"abfall":"2|3", "jahr": datetime.datetime.now().year, "service":"augsburglandkreis"}}


BASE_URL = "https://web.c-trace.de"
SERVICE_MAP = {"Bremen": "bremenabfallkalender"}



class Source:
    def __init__(self, ort, strasse, hausnummer,service, abfall,jahr):
        self._ort = ort
        self._strasse = strasse
        self._hausnummer = hausnummer
        self._service = service
        self._abfall= abfall
        self._jahr=jahr
        self._ics = ICS(regex=r"Abfuhr: (.*)")


    def fetch(self):
        service = SERVICE_MAP.get(self._ort) if self._service else self._service 
        if service is None:
            raise Exception(f"no service for {self._ort}")

        session = requests.session()

        # get session url
        r = session.get(
            f"{BASE_URL}/{self._service}/Abfallkalender",
            allow_redirects=False,
        )
        session_id = r.headers["location"].split("/")[
            2
        ]  # session_id like "(S(r3bme50igdgsp2lstgxxhvs2))"

        args = {
            "Ort": self._ort,
            "Gemeinde": self._ort,
            "Strasse": self._strasse,
            "Hausnr": self._hausnummer,
            "Abfall":self._abfall,
            "Jahr": self._jahr
        }
        r = session.get(
            f"{BASE_URL}/{self._service}/{session_id}/abfallkalender/cal", params=args
        )
        r.raise_for_status()

        # parse ics file
        r.encoding = "utf-8"
        dates = self._ics.convert(r.text)

        entries = []
        for d in dates:
            entries.append(Collection(d[0], d[1]))
        return entries
