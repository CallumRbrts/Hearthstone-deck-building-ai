import os.path
import random
from bisect import bisect
from importlib import import_module
from pkgutil import iter_modules
from typing import List
from xml.etree import ElementTree
from fireplace.exceptions import GameOver


from hearthstone.enums import CardClass, CardType


# Autogenerate the list of cardset modules
_cards_module = os.path.join(os.path.dirname(__file__), "cards")
CARD_SETS = [cs for _, cs, ispkg in iter_modules([_cards_module]) if ispkg]


class CardList(list):
	def __contains__(self, x):
		for item in self:
			if x is item:
				return True
		return False

	def __getitem__(self, key):
		ret = super().__getitem__(key)
		if isinstance(key, slice):
			return self.__class__(ret)
		return ret

	def __int__(self):
		# Used in Kettle to easily serialize CardList to json
		return len(self)

	def contains(self, x):
		"""
		True if list contains any instance of x
		"""
		for item in self:
			if x == item:
				return True
		return False

	def index(self, x):
		for i, item in enumerate(self):
			if x is item:
				return i
		raise ValueError

	def remove(self, x):
		for i, item in enumerate(self):
			if x is item:
				del self[i]
				return
		raise ValueError

	def exclude(self, *args, **kwargs):
		if args:
			return self.__class__(e for e in self for arg in args if e is not arg)
		else:
			return self.__class__(e for k, v in kwargs.items() for e in self if getattr(e, k) != v)

	def filter(self, **kwargs):
		return self.__class__(e for k, v in kwargs.items() for e in self if getattr(e, k, 0) == v)


def random_draft(card_class: CardClass, exclude=[]):
	"""
	Return a deck of 30 random cards for the \a card_class
	"""
	from fireplace import cards
	from fireplace.deck import Deck

	deck = []
	collection = []
	# hero = card_class.default_hero

	for card in cards.db.keys():
		if card in exclude:
			continue
		cls = cards.db[card]
		if not cls.collectible:
			continue
		if cls.type == CardType.HERO:
			# Heroes are collectible...
			continue
		if cls.card_class and cls.card_class not in [card_class, CardClass.NEUTRAL]:
			# Play with more possibilities
			continue
		collection.append(cls)

	while len(deck) < Deck.MAX_CARDS:
		card = random.choice(collection)
		if deck.count(card.id) < card.max_count_in_deck:
			deck.append(card.id)

	return deck


def random_class():
	return CardClass(random.randint(2, 10))


def get_script_definition(id):
	"""
	Find and return the script definition for card \a id
	"""
	for cardset in CARD_SETS:
		module = import_module("fireplace.cards.%s" % (cardset))
		if hasattr(module, id):
			return getattr(module, id)


def entity_to_xml(entity):
	e = ElementTree.Element("Entity")
	for tag, value in entity.tags.items():
		if value and not isinstance(value, str):
			te = ElementTree.Element("Tag")
			te.attrib["enumID"] = str(int(tag))
			te.attrib["value"] = str(int(value))
			e.append(te)
	return e


def game_state_to_xml(game):
	tree = ElementTree.Element("HSGameState")
	tree.append(entity_to_xml(game))
	for player in game.players:
		tree.append(entity_to_xml(player))
	for entity in game:
		if entity.type in (CardType.GAME, CardType.PLAYER):
			# Serialized those above
			continue
		e = entity_to_xml(entity)
		e.attrib["CardID"] = entity.id
		tree.append(e)

	return ElementTree.tostring(tree)


def weighted_card_choice(source, weights: List[int], card_sets: List[str], count: int):
	"""
	Take a list of weights and a list of card pools and produce
	a random weighted sample without replacement.
	len(weights) == len(card_sets) (one weight per card set)
	"""

	chosen_cards = []

	# sum all the weights
	cum_weights = []
	totalweight = 0
	for i, w in enumerate(weights):
		totalweight += w * len(card_sets[i])
		cum_weights.append(totalweight)

	# for each card
	for i in range(count):
		# choose a set according to weighting
		chosen_set = bisect(cum_weights, random.random() * totalweight)

		# choose a random card from that set
		chosen_card_index = random.randint(0, len(card_sets[chosen_set]) - 1)

		chosen_cards.append(card_sets[chosen_set].pop(chosen_card_index))
		totalweight -= weights[chosen_set]
		cum_weights[chosen_set:] = [x - weights[chosen_set] for x in cum_weights[chosen_set:]]

	return [source.controller.card(card, source=source) for card in chosen_cards]


def setup_game(deck, player_name, opponents_deck):
	from fireplace.game import Game
	from fireplace.player import Player

	#Some cards from these decks aren't implemented which means that they won't have an effect,
	#if they are a minion then it will have it's stats but not the battlecry effect, spell will just do nothing
	#either implement it or talk about it
	deck1 = deck
	deck2 = opponents_deck

	#global so it can carry over to other functions
	global name
	name = player_name

	#It seems that player classes influence the deck win rate, Hunters win more than Warlocks due to the dumb AI
	player1 = Player(name, deck1, CardClass.WARRIOR.default_hero)
	player2 = Player("Oppenent", deck2, CardClass.MAGE.default_hero)

	game = Game(players=(player1, player2))
	game.start()

	return game


def play_turn(game):
	player = game.current_player

	while True:
		heropower = player.hero.power
		if heropower.is_usable() and random.random() < 0.1:
			if heropower.requires_target():
				heropower.use(target=random.choice(heropower.targets))
			else:
				heropower.use()
			continue

		# iterate over our hand and play whatever is playable
		for card in player.hand:
			if card.is_playable() and random.random() < 0.5:
				target = None
				if card.must_choose_one:
					card = random.choice(card.choose_cards)
				if card.requires_target():
					target = random.choice(card.targets)
				print("Playing %r on %r" % (card, target))
				card.play(target=target)

				if player.choice:
					choice = random.choice(player.choice.cards)
					print("Choosing card %r" % (choice))
					player.choice.choose(choice)

				continue
		# added GameOver try catch to catch the winner of the match and send it to a result.txt file
		# Randomly attack with whatever can attack
		try:
			for character in player.characters:
				if character.can_attack():
					character.attack(random.choice(character.targets))
		except GameOver:
			print('Game End')
			#for some reason the players are sometimes switched (so player 1 becomes player 2), to avoid this I have written this code
			if game.player1.name == name:
				print(game.player1.name, game.player1.hero, game.player1.playstate)
				with open('results.txt', 'w') as f:
					print(game.player1.playstate, file=f)
			elif game.player2.name == name:
				print(game.player2.name, game.player2.hero, game.player2.playstate)
				with open('results.txt', 'w') as f:
					print(game.player2.playstate, file=f)
		break

	game.end_turn()
	return game


def play_full_game(deck,player_name,opponents_deck):
	game = setup_game(deck,player_name,opponents_deck)

	for player in game.players:
		print("Can mulligan %r" % (player.choice.cards))
		mull_count = random.randint(0, len(player.choice.cards))
		cards_to_mulligan = random.sample(player.choice.cards, mull_count)
		player.choice.choose(*cards_to_mulligan)

	while True:
		play_turn(game)

	return game