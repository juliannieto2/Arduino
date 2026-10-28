"""
Warehouse Logic and Data Model for Automated Picking Simulation.
"""

import math
from typing import Dict, Tuple, List, Optional

# Definition of Satellite Storage Locations (Sud 1 to Sud 63)
# Map: Sud_ID -> {aisle: str, side: str, depth_index: int (1..9)}
# Depth index 1 is closest to SALIDA (high popularity), 9 is furthest back (low popularity).

AISLE_MAPPING: Dict[int, Dict[str, object]] = {}

# Pasillo A: Sud 1 to Sud 9 (Single rack on left of aisle A)
for i in range(1, 10):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo A",
        "side": "left",
        "depth_index": i  # 1 nearest to SALIDA, 9 furthest
    }

# Pasillo B: Sud 10 to Sud 18 (left rack) & Sud 19 to Sud 27 (right rack)
for i in range(10, 19):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo B",
        "side": "left",
        "depth_index": i - 9
    }
for i in range(19, 28):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo B",
        "side": "right",
        "depth_index": i - 18
    }

# Pasillo C: Sud 28 to Sud 36 (left rack) & Sud 37 to Sud 45 (right rack)
for i in range(28, 37):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo C",
        "side": "left",
        "depth_index": i - 27
    }
for i in range(37, 46):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo C",
        "side": "right",
        "depth_index": i - 36
    }

# Pasillo D: Sud 46 to Sud 54
for i in range(46, 55):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo D",
        "side": "right",
        "depth_index": i - 45
    }

# Pasillo E: Sud 55 to Sud 63
for i in range(55, 64):
    AISLE_MAPPING[i] = {
        "aisle": "Pasillo E",
        "side": "right",
        "depth_index": i - 54
    }

AISLES = ["Pasillo A", "Pasillo B", "Pasillo C", "Pasillo D", "Pasillo E"]
LEVELS = [1, 2]


class WarehouseModel:
    def __init__(self):
        self.total_suds = 63
        self.aisle_mapping = AISLE_MAPPING

    def get_location_info(self, sud_id: int) -> Optional[Dict[str, object]]:
        return self.aisle_mapping.get(sud_id)

    def get_popularity_score(self, sud_id: int) -> float:
        """
        Returns a score from 1.0 (highest popularity, closest to SALIDA)
        to 0.0 (lowest popularity, furthest back).
        """
        info = self.get_location_info(sud_id)
        if not info:
            return 0.0
        depth = info["depth_index"]  # 1 to 9
        # Score linearly decreases from depth 1 to depth 9
        return round(1.0 - (depth - 1) / 8.0, 2)

    def get_popularity_color(self, sud_id: int) -> Tuple[int, int, int]:
        """
        Returns an RGB tuple representing popularity heat map color.
        High popularity (1.0): Green (46, 204, 113) -> Yellow (241, 196, 15) -> Orange/Red/Grey (231, 76, 60 / 149, 165, 166)
        """
        score = self.get_popularity_score(sud_id)
        if score >= 0.75:
            # High rot: Green shades
            return (46, 204, 113)
        elif score >= 0.50:
            # Medium-High: Yellow/Green
            return (241, 196, 15)
        elif score >= 0.25:
            # Medium-Low: Orange
            return (230, 126, 34)
        else:
            # Low rot: Red/Grey
            return (180, 100, 100)

    def generate_arduino_cmd(self, sud_id: int, level: int, action: str = "PICK") -> List[str]:
        """
        Generates simulated Arduino serial log outputs.
        """
        info = self.get_location_info(sud_id)
        if not info:
            return [f"[ARDUINO] ERROR: Posición Sud {sud_id} no válida."]

        aisle = info["aisle"]
        level_str = f"Nivel {level:02d}"

        logs = [
            f"[ARDUINO] Recibida orden de comando -> Destino: Sud {sud_id} ({aisle}), {level_str}, Acción: {action}",
            f"[ARDUINO] Iniciando motores de tracción horizontal...",
            f"[ARDUINO] Navegando por pasillo principal -> Entrando a {aisle}...",
            f"[ARDUINO] Posición alcanzada: Sud {sud_id}.",
            f"[ARDUINO] Desplegando actuador vertical -> Elevando a {level_str}...",
            f"[ARDUINO] Actuador fijado en {level_str}. Ejecutando maniobra de {action}...",
            f"[ARDUINO] Operación de {action} completada con éxito.",
            f"[ARDUINO] Repliegue de actuador a Nivel 01. Retornando robot a zona de SALIDA..."
        ]
        return logs


if __name__ == "__main__":
    wm = WarehouseModel()
    print("Warehouse model initialized successfully.")
    print(f"Sud 1 info: {wm.get_location_info(1)}, Popularity: {wm.get_popularity_score(1)}")
    print(f"Sud 14 info: {wm.get_location_info(14)}, Popularity: {wm.get_popularity_score(14)}")
    print(f"Sud 63 info: {wm.get_location_info(63)}, Popularity: {wm.get_popularity_score(63)}")
    for log in wm.generate_arduino_cmd(14, 2):
        print(log)
