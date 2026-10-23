import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_fixture_loop import geometry


class FixtureLoopGeometryTests(unittest.TestCase):
    def samples(self):
        truth = [{'stamp_ns': i*20_000_000,'xyz':[i*.001,0,0],
                  'q_xyzw':[0,0,0,1]} for i in range(52)]
        graph = [{'index':0,'source_ns':0,'loop_index':-1},
                 {'index':51,'source_ns':1_020_000_000,'loop_index':0,
                  'loop_relative_t':[.051,0,0],'loop_relative_q_xyzw':[0,0,0,1]}]
        return graph,truth

    def test_true_edge_and_wrong_edge_are_distinguished(self):
        graph,truth=self.samples()
        self.assertAlmostEqual(geometry(graph,truth,[0,0,0])[0]['translation_error_m'],0)
        graph[-1]['loop_relative_t']=[1,0,0]
        self.assertGreater(geometry(graph,truth,[0,0,0])[0]['translation_error_m'],.9)

    def test_adjacent_and_uncovered_edges_are_rejected(self):
        graph,truth=self.samples()
        graph[-1]['index']=49
        with self.assertRaises(ValueError):geometry(graph,truth,[0,0,0])
        graph,truth=self.samples()
        with self.assertRaises(ValueError):geometry(graph,truth[:-3],[0,0,0])


if __name__=='__main__':unittest.main()
