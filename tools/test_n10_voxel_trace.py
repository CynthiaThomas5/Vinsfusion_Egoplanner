import unittest

from tools.debug_truth.evaluate_n10_voxel_trace import decode_voxel_update


class N10VoxelTraceDecoderTests(unittest.TestCase):
    def test_decodes_compact_v2_vote_and_class_codes(self):
        row = {
            'schema': 'n10-voxel-update-trace/v2',
            'update_fields': [
                'ix', 'iy', 'iz', 'hit_votes', 'miss_votes', 'pre_log_odds',
                'post_log_odds', 'pre_class_code', 'post_class_code',
            ],
        }
        result = decode_voxel_update(row, [12, 34, 5, 2, 1, -0.4, 0.1, 0, 1])
        self.assertEqual(result, {
            'index': [12, 34, 5],
            'hit_votes': 2,
            'miss_votes': 1,
            'selected_vote': 'hit',
            'pre_class': 'unknown',
            'post_class': 'free',
        })

    def test_decodes_legacy_v1_object(self):
        row = {'schema': 'n10-voxel-update-trace/v1'}
        result = decode_voxel_update(row, {
            'index': [1, 2, 3],
            'hit_votes': 0,
            'miss_votes': 3,
            'selected_vote': 'miss',
            'pre_class': 'occupied',
            'post_class': 'free',
        })
        self.assertEqual(result['index'], [1, 2, 3])
        self.assertEqual(result['selected_vote'], 'miss')
        self.assertEqual(result['pre_class'], 'occupied')

    def test_rejects_wrong_compact_field_order(self):
        with self.assertRaisesRegex(ValueError, 'field order'):
            decode_voxel_update({
                'schema': 'n10-voxel-update-trace/v2',
                'update_fields': ['wrong'],
            }, [0])


if __name__ == '__main__':
    unittest.main()
