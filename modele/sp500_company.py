from dataclasses import asdict, dataclass


@dataclass
class SP500Company:
    symbol: str
    security: str
    gics_sector: str
    gics_sub_industry: str
    headquarters_location: str
    date_added: str
    cik: str
    founded: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
