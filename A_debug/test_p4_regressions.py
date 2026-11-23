import unittest

from p4_keep_original_policy import get_baseline_alert_status, apply_failure
from p4_vehicle_state import BASELINE_PLAN
from main_experiments import SCENARIOS, run_reschedule_pipeline


class P4DebugRegressionTests(unittest.TestCase):
    def test_baseline_plan_alerts_are_pairs(self):
        status = get_baseline_alert_status()
        self.assertEqual(set(status), {"ALERT_001", "ALERT_002", "ALERT_003"})
        for info in status.values():
            self.assertEqual(len(info["vehicles"]), 2)

    def test_failure_before_observation_does_not_count_partial_joint_alert(self):
        timeline = {vid: [dict(task) for task in tasks]
                   for vid, tasks in BASELINE_PLAN.items()}
        status = get_baseline_alert_status()
        apply_failure(timeline, status, "V1", 5.0)
        self.assertFalse(status["ALERT_002"]["started"])
        self.assertEqual(status["ALERT_002"]["vehicles"], [])

    def test_baseline_vehicle_tasks_do_not_overlap(self):
        for vid, tasks in BASELINE_PLAN.items():
            ordered = sorted(tasks, key=lambda task: task["depart"])
            for left, right in zip(ordered, ordered[1:]):
                self.assertLessEqual(left["reset_end"], right["depart"] + 1e-8, vid)

    def test_disruption_scenarios_have_consistent_nonoverlap_timeline(self):
        for key in ("S1", "S2", "S4", "S5", "S6", "S7"):
            with self.subTest(scenario=key):
                result = run_reschedule_pipeline(SCENARIOS[key])
                timeline = result["timeline"]
                for vid, tasks in timeline.items():
                    active = sorted((t for t in tasks if t.get("status") == "completed"),
                                    key=lambda t: t["depart"])
                    for left, right in zip(active, active[1:]):
                        self.assertLessEqual(left["reset_end"], right["depart"] + 1e-8, vid)
                for alert_id, info in result["alert_status"].items():
                    if info.get("started"):
                        self.assertEqual(len(info.get("vehicles", [])), 2, alert_id)
                        self.assertLessEqual(info["observe_start"], 60.0 + 1e-8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
