"""
Testes unitários para o módulo geoespacial.

Autora: Vanessa Batista (@vandromedae)
Repositório: https://github.com/vandromedae/desertos-medicos-sus
Licença: MIT (https://github.com/vandromedae/desertos-medicos-sus/blob/main/LICENSE)

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from src.geospatial import parse_location_wkt


class TestParseLocationWkt:
    """Testes para parse_location_wkt."""

    def test_wkt_point_format(self):
        assert parse_location_wkt("POINT (-46.6333 -23.5505)") == (-46.6333, -23.5505)

    def test_wkt_point_no_spaces(self):
        assert parse_location_wkt("POINT(-46.6333 -23.5505)") == (-46.6333, -23.5505)

    def test_comma_separated_lon_lat(self):
        assert parse_location_wkt("-46.6333,-23.5505") == (-46.6333, -23.5505)

    def test_comma_separated_with_spaces(self):
        assert parse_location_wkt("-46.6333, -23.5505") == (-46.6333, -23.5505)

    def test_comma_heuristic_lat_first(self):
        # lat first, lon second (ambiguous) — defaults to lon,lat order
        assert parse_location_wkt("-23.5505,-46.6333") == (-23.5505, -46.6333)

    def test_comma_heuristic_lon_outside_lat_range(self):
        # val1 in lat range, val2 outside → val2 is lon
        assert parse_location_wkt("-23.5,-100.0") == (-100.0, -23.5)

    def test_comma_heuristic_lat_outside_lon_range(self):
        # val1 outside lat range, val2 in → val1 is lon
        assert parse_location_wkt("-100.0,-23.5") == (-100.0, -23.5)

    def test_none_input(self):
        assert parse_location_wkt(None) is None

    def test_nan_input(self):
        import math
        assert parse_location_wkt(float("nan")) is None

    def test_empty_string(self):
        assert parse_location_wkt("") is None

    def test_dash_input(self):
        assert parse_location_wkt("-") is None

    def test_invalid_string(self):
        assert parse_location_wkt("invalid") is None

    def test_single_value(self):
        assert parse_location_wkt("-46.6333") is None

    def test_three_values(self):
        assert parse_location_wkt("-46.6333,-23.5505,100") is None

    def test_wkt_with_extra_parts(self):
        # Extra parts after coordinates are ignored
        assert parse_location_wkt("POINT (-46.6333 -23.5505 0)") == (-46.6333, -23.5505)
