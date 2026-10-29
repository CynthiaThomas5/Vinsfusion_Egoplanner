"""Normal controller-session end must retire held planner references."""
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/own/uav_navigation'))
from uav_navigation.node import NavigationNode
from uav_navigation.task_state import NavigationGoal, TaskSupervisor
from uav_interfaces.msg import TrajectoryCancel

class BridgeCloseoutTests(unittest.TestCase):
    def node(self, active=False):
        published=[]
        core=TaskSupervisor();core.update_localization('epoch-a',True,True,'tracking')
        if active:
            core.submit(NavigationGoal('goal-a','epoch-a',(1.,0.,1.),0.,.2,.2,1.,60.),1.)
        n=SimpleNamespace(_lock=threading.RLock(),core=core,
            _forwarded_goals={'goal-a':'epoch-a'},_goal_epochs={'goal-a':'epoch-a'},
            _terminal_events={},_trajectory_cancel_pub=SimpleNamespace(publish=published.append))
        n._clear_forwarded=lambda reason:NavigationNode._clear_forwarded(n,reason)
        n._process_events=lambda events:NavigationNode._process_events(n,events)
        return n,published

    def test_completed_goal_hold_survives_active_and_takeoff(self):
        for phase in ('ACTIVE','TAKEOFF'):
            n,p=self.node();NavigationNode._on_bridge(n,SimpleNamespace(phase=phase,epoch='epoch-a'))
            self.assertEqual(p,[]);self.assertEqual(n._forwarded_goals,{'goal-a':'epoch-a'})

    def test_normal_landing_retires_completed_hold_once_with_exact_identity(self):
        n,p=self.node()
        for phase in ('LANDING','LANDED','DISABLED'):
            NavigationNode._on_bridge(n,SimpleNamespace(phase=phase,epoch='epoch-a'))
        self.assertEqual(len(p),1)
        self.assertEqual((p[0].goal_id,p[0].epoch,p[0].mode),('goal-a','epoch-a',TrajectoryCancel.MODE_ABORT))
        self.assertEqual(n._forwarded_goals,{})
        self.assertEqual(n._terminal_events,{})

    def test_bridge_message_from_another_epoch_does_not_retire_current_hold(self):
        n,p=self.node();NavigationNode._on_bridge(n,SimpleNamespace(phase='LANDED',epoch='old'))
        self.assertEqual(p,[]);self.assertIn('goal-a',n._forwarded_goals)

    def test_existing_landing_ends_running_goal_without_repeated_cancel(self):
        n,p=self.node(active=True)
        NavigationNode._on_bridge(n,SimpleNamespace(phase='LANDING',epoch='epoch-a'))
        self.assertIsNone(n.core.active_goal);self.assertEqual(len(p),1)
        self.assertEqual(n._terminal_events['goal-a'][0].reason,'bridge_control_session_ended')

if __name__=='__main__':unittest.main()
