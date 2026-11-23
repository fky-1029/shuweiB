import unittest
from unittest.mock import patch

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
                    active = sorted((t for t in tasks if t.get("status") in {"completed", "locked"}),
                                    key=lambda t: t["depart"])
                    for left, right in zip(active, active[1:]):
                        self.assertLessEqual(left["reset_end"], right["depart"] + 1e-8, vid)
                for alert_id, info in result["alert_status"].items():
                    if info.get("started"):
                        self.assertEqual(len(info.get("vehicles", [])), 2, alert_id)
                        self.assertLessEqual(info["observe_start"], 60.0 + 1e-8)

    def test_started_before_failure_is_never_rescheduled_even_during_observation(self):
        # V3/V5 的 T1 在 1.7519 开始、6.7519 结束；5 秒时仍在观测。
        for failed_vehicle in ("V3", "V5"):
            with self.subTest(failed_vehicle=failed_vehicle):
                with patch("main_experiments.apply_reschedule", return_value={"schedule": []}) as scheduler:
                    result = run_reschedule_pipeline({
                        "new_alert": None, "failed_vehicle": failed_vehicle,
                        "recovery_time": None,
                    })
                if scheduler.called:
                    self.assertNotIn("ALERT_001", [t["task_id"] for t in scheduler.call_args.args[0]])
                self.assertTrue(result["alert_status"]["ALERT_001"]["started"])
                self.assertEqual(result["alert_status"]["ALERT_001"]["observe_start"], 1.7519)
                for vid in ("V3", "V5"):
                    task = next(t for t in result["timeline"][vid] if t["task_id"] == "ALERT_001")
                    self.assertIn(task["status"], {"completed", "locked"})

    def test_exactly_at_disturbance_is_not_locked(self):
        # 人工调整一项基准告警的双车同步观测开始到 t=5，验证严格边界。
        from main_experiments import BASELINE_PLAN as plan
        with patch.dict(plan, {vid: [dict(t) for t in entries] for vid, entries in plan.items()},
                        clear=True):
            for vid in ("V3", "V5"):
                task = plan[vid][0]
                task["observe_start"] = 5.0
                task["observe_end"] = 10.0
                task["reset_end"] = 11.0
            # 顺延 V5 后续任务，维持人工时间线自身的先后约束。
            second = plan["V5"][1]
            second["depart"] = 11.0
            second["travel_end"] = 11.0
            second["gimbal_ready"] = 13.7552
            second["observe_start"] = 13.7552
            second["observe_end"] = 18.7552
            second["reset_end"] = 21.5105
            plan["V2"][0]["observe_start"] = 13.7552
            plan["V2"][0]["observe_end"] = 18.7552
            plan["V2"][0]["reset_end"] = 24.4950
            with patch("main_experiments.apply_reschedule", return_value={"schedule": []}) as scheduler:
                run_reschedule_pipeline({"new_alert": None, "failed_vehicle": "V3",
                                         "recovery_time": None})
            self.assertIn("ALERT_001", [t["task_id"] for t in scheduler.call_args.args[0]])

    def test_recovery_keeps_prior_and_inflight_alerts_without_repeating(self):
        # 恢复于 15 秒：T1 已开始；T2、T3 已按原命令出发。
        for scenario in ("S5", "S6", "S7"):
            with self.subTest(scenario=scenario):
                with patch("main_experiments.apply_reschedule") as scheduler:
                    result = run_reschedule_pipeline(SCENARIOS[scenario])
                selected = [t["task_id"] for t in scheduler.call_args.args[0]]
                self.assertNotIn("ALERT_001", selected)
                if scenario == "S5":
                    self.assertEqual(selected, ["NEW_ALERT"])
                else:
                    self.assertEqual(set(selected), {"ALERT_003"} |
                                     ({"NEW_ALERT"} if scenario == "S7" else set()))
                for vid in ("V3", "V5"):
                    task = next(t for t in result["timeline"][vid] if t["task_id"] == "ALERT_001")
                    self.assertIn(task["status"], {"completed", "locked"})
                for vid, entries in result["timeline"].items():
                    active = sorted((t for t in entries if t["status"] in {"completed", "locked"}),
                                    key=lambda t: t["depart"])
                    for previous, current in zip(active, active[1:]):
                        self.assertGreaterEqual(current["depart"] + 1e-8, previous["reset_end"], vid)
                if scenario == "S5":
                    self.assertEqual(len([t for entries in result["timeline"].values()
                                          for t in entries if t["task_id"] == "ALERT_003"
                                          and t["status"] in {"completed", "locked"}]), 2)

    def test_recovery_does_not_release_vehicle_during_gimbal_reset(self):
        # 恢复 7 秒时 T1 观测已结束，但 V3/V5 分别到 7.7683/8.2682 才复位。
        config = dict(SCENARIOS["S5"], recovery_time=7.0)
        with patch("main_experiments.apply_reschedule", return_value={"schedule": []}) as scheduler:
            run_reschedule_pipeline(config)
        states = scheduler.call_args.args[1]
        self.assertGreaterEqual(states["V3"]["available_time"], 7.7683)
        self.assertGreaterEqual(states["V5"]["available_time"], 8.2682)
        self.assertEqual(states["V5"]["position"], (49.5, 93.5))

    def test_failed_joint_task_keeps_dispatched_partner_busy_until_reset(self):
        # V2 在 t=5 故障；V5 在中断期间依旧执行已下发的 T3 原命令。
        with patch("main_experiments.apply_reschedule", return_value={"schedule": []}) as scheduler:
            result = run_reschedule_pipeline(SCENARIOS["S6"])
        states = scheduler.call_args.args[1]
        self.assertTrue(states["V2"]["failed"])
        self.assertEqual(states["V5"]["position"], (49.5, 93.5))
        self.assertGreaterEqual(states["V5"]["available_time"], 18.7787)
        old = next(t for t in result["timeline"]["V5"] if t["task_id"] == "ALERT_003")
        self.assertEqual(old["status"], "locked")
        self.assertFalse(result["alert_status"]["ALERT_003"]["started"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
