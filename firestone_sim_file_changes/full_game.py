#!/usr/bin/env python
import sys

from fireplace import cards
from fireplace.exceptions import GameOver


from utils_fireplace import play_full_game


sys.path.append("..")


def test_full_game(deck,player_name,opponents_deck):
	try:
		print(deck)
		play_full_game(deck,player_name,opponents_deck)
	except GameOver:
		print("Game completed normally.")


def main():
	#deck = ['YOP_015', 'YOP_013', 'YOP_013', 'BT_233', 'DRG_239', 'BT_722', 'CS2_104', 'DAL_759', 'CS2_104', 'DMF_189', 'ULD_309', 'BT_781', 'DRG_025', 'EX1_084', 'DMF_530', 'YOD_024', 'SCH_521', 'BT_140', 'SCH_317', 'DRG_020', 'DRG_022', 'EX1_507', 'EX1_020', 'YOP_005', 'BT_190', 'DMF_528', 'ULD_707', 'ULD_253', 'SCH_337', 'DAL_059']
	deck = sys.argv[1]
	player_name = sys.argv[2]
	opponents_deck = sys.argv[3]
	cards.db.initialize()
	test_full_game(deck,player_name,opponents_deck)


if __name__ == "__main__":
	main()
