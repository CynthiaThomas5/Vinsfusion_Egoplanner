import unittest
from tools.n16_process_lifecycle import assess_lifecycle,CORE_ROLES

class ProcessLifecycleTests(unittest.TestCase):
    def fixture(self):
        roles={k:['10:100'] for k in CORE_ROLES}
        return [{'run_id':'run','expected_roles':list(CORE_ROLES),'safe_terminal_observed':True},
                [{'sim_ns':None,'roles':roles}],{'run_id':'run','runner_identities_observed_while_alive':['20:200']},
                [{'sim_ns':400,'roles':roles}],0,300,'run']
    def test_birth_before_runner_and_alive_after_end(self):
        self.assertEqual(assess_lifecycle(*self.fixture())['status'],'PASS')
    def test_reused_pid_with_new_birth_not_accepted(self):
        f=self.fixture();f[3][0]['roles']={k:['10:250'] for k in CORE_ROLES}
        self.assertEqual(assess_lifecycle(*f)['status'],'INSUFFICIENT')
    def test_core_born_after_runner_not_accepted(self):
        f=self.fixture();f[2]['runner_identities_observed_while_alive']=['20:50']
        self.assertEqual(assess_lifecycle(*f)['status'],'INSUFFICIENT')
    def test_snapshot_before_window_end_not_enough(self):
        f=self.fixture();f[3][0]['sim_ns']=299
        self.assertEqual(assess_lifecycle(*f)['status'],'INSUFFICIENT')
