import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "05_TOOLS", "sol_mind"))
import model_router as MR


class SummonHelicopterMindContract(unittest.TestCase):
    def test_command_is_indexed_and_has_exact_phrase_example(self):
        action = "sol_summon_helicopter"
        self.assertIn(action, MR.COMMANDS)
        examples = MR.example_bank([])
        self.assertTrue(any(action in answer and "سول فيكي تجيبي هليكوبتر" in phrase
                            for phrase, answer in examples))

    def test_specific_reply_is_in_route_implementation(self):
        path = os.path.join(ROOT, "05_TOOLS", "sol_mind", "chat_service.py")
        source = Path(path).read_text(encoding="utf-8")
        self.assertIn('action = "sol_summon_helicopter"', source)
        self.assertIn('return "أكيد بقدر"', source)
        self.assertIn('"explicit-intent"', source)

    def test_server_spawn_is_allowlisted_and_server_authoritative(self):
        path = os.path.join(ROOT, "01_WORK", "Sol", "42", "media", "lua", "server",
                            "SolHelicopterSummonServer.lua")
        source = Path(path).read_text(encoding="utf-8")
        for required in ("registry.GetAircraft", 'aircraft.category ~= "helicopter"',
                         "findSpawnSquare", "addVehicle", '"JetFuel"',
                         "setContainerContentAmount", "isSafeToSpawn", "Events.OnClientCommand"):
            self.assertIn(required, source)
        self.assertNotIn("addVehicleDebug", source)

    def test_kahlua_invoke_results_are_collapsed_before_numeric_conversion(self):
        path = os.path.join(ROOT, "01_WORK", "Sol", "42", "media", "lua", "server",
                            "SolHelicopterSummonServer.lua")
        source = Path(path).read_text(encoding="utf-8")
        self.assertIn("local value = invoke(object, name, ...)", source)
        self.assertNotIn("tonumber(invoke(", source)
        self.assertIn('numberMethod(player, "getX")', source)
        self.assertIn('numberMethod(tank, "getContainerContentAmount")', source)

    def test_aviationcore_modules_are_captured_from_require_returns(self):
        path = os.path.join(ROOT, "01_WORK", "Sol", "42", "media", "lua", "server",
                            "SolHelicopterSummonServer.lua")
        source = Path(path).read_text(encoding="utf-8")
        self.assertIn('local AircraftFactoryParts = require "AviationCore/AircraftFactoryParts"', source)
        self.assertIn('local OperatorManuals = require "AviationCore/OperatorManuals"', source)
        self.assertIn('type(AircraftFactoryParts.FinalizeVehicle) == "function"', source)
        self.assertIn('local ok, finalized, reason = pcall(AircraftFactoryParts.FinalizeVehicle,', source)


if __name__ == "__main__":
    unittest.main()
