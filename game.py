# -*- coding: utf-8 -*-
#
#  Game.py, Ice Emblem's main game class.
#
#  Copyright 2015 Elia Argentieri <elia.argentieri@openmailbox.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import pygame
from pygame.locals import *
import os
import logging
import traceback

import display
import resources
import sounds
import events
import map
import gui
import utils
import ai
import room
from display import window
from colors import *


TIME_BETWEEN_ATTACKS = 2000  # Time to wait between each attack animation
font_name = os.path.join('Medieval Sharp', 'MedievalSharp.ttf')
MAIN_MENU_FONT = resources.load_font(font_name, 48)
MAIN_FONT = resources.load_font(font_name, 36)
SMALL_FONT = resources.load_font(font_name, 24)


loaded_map = None
units_manager = None
winner = None


def load_map(map_path):
	global loaded_map, units_manager
	if map_path is not None:
		try:
			loaded_map = map.Map(map_path)
			units_manager = loaded_map.units_manager
			for team in units_manager.teams:
				if team.ai:
					team.ai = ai.AI(loaded_map, units_manager, team)
			events.register(VIDEORESIZE, loaded_map.handle_videoresize)
		except:
			msg = _("Can't load map %s! Probabily the format is not ok.\n%s") % (resources.map_path(files[menu.choice][0]), traceback.format_exc())
			logging.error(msg)
			dialog = gui.Dialog(msg, SMALL_FONT, (100, 100))
			events.new_context("MapError")
			dialog.register("MapError")
			def event_loop(_events):
				dialog.draw()
				display.clock.tick(60)
				pygame.display.flip()
				return dialog.ok
			events.event_loop(event_loop, True, "MapError")
	else:
		loaded_map = None
		units_manager = None


def kill(unit):
	loaded_map.kill_unit(unit=unit)
	units_manager.kill_unit(unit)
	self.winner = None
	self.state = 0
	self.prev_coord = None

def experience_animation(unit, bg):
	img_pos = utils.center(window.get_rect(), unit.image.get_rect())
	exp_pos = (img_pos[0], img_pos[1] + unit.image.get_height() + 50)

	sounds.play('exp', -1)

	gained_exp = unit.gained_exp()
	curr_exp = unit.prev_exp
	while curr_exp <= gained_exp + unit.prev_exp:
		if unit.levelled_up() and curr_exp == 100:
			sounds.play('levelup')
		exp = pygame.Surface((curr_exp % 100, 20))
		exp.fill(YELLOW)

		exp_text = SMALL_FONT.render(_("EXP: %d") % (curr_exp % 100), True, YELLOW)
		lv_text = SMALL_FONT.render(_("LV: %d") % unit.level, True, BLUE)

		window.blit(bg, (0, 0))
		window.blit(unit.image, img_pos)
		window.blit(exp, exp_pos)
		window.blit(exp_text, (exp_pos[0], exp_pos[1] + 25))
		window.blit(lv_text, (exp_pos[0] + exp_text.get_width() + 10, exp_pos[1] + 25))

		curr_exp += 1
		pygame.display.flip()
		display.clock.tick(60)
		events.pump()

	sounds.stop('exp')
	events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
	events.wait(timeout=2000)


def attack(attacking, defending):
	global winner
	events.new_context("Battle")
	attacking_team = units_manager.get_team(attacking.color)
	defending_team = units_manager.get_team(defending.color)

	att_weapon = attacking.items.active
	def_weapon = defending.items.active

	attacking.prepare_battle()
	defending.prepare_battle()

	dist = utils.distance(attacking.coord, defending.coord)
	at, dt = attacking.number_of_attacks(defending, dist)

	print("\r\n" + "#" * 12 + " " + _("Fight!!!") + " " + "#" * 12)
	att_str = _("%s is going to attack %d %s")
	print(att_str % (attacking.name, at, _("time") if at == 1 else _("times")))
	print(att_str % (defending.name, dt, _("time") if dt == 1 else _("times")))

	attacking_team.play_music('battle')

	loaded_map.draw(window)
	display.fadeout(1000, 10)  # Darker atmosphere

	battle_background = window.copy()

	att_swap = attacking
	def_swap = defending

	att_name = MAIN_FONT.render(attacking.name, 1, attacking_team.color)
	def_name = MAIN_FONT.render(defending.name, 1, defending_team.color)

	miss_text = SMALL_FONT.render(_("MISS"), 1, YELLOW).convert_alpha()
	null_text = SMALL_FONT.render(_("NULL"), 1, RED).convert_alpha()
	crit_text = SMALL_FONT.render(_("TRIPLE"), 1, RED).convert_alpha()
	screen_rect = window.get_rect()

	att_rect_origin = attacking.image.get_rect(centerx=screen_rect.centerx-screen_rect.centerx//2, bottom=screen_rect.centery-25)
	def_rect_origin = defending.image.get_rect(centerx=screen_rect.centerx+screen_rect.centerx//2, bottom=screen_rect.centery-25)
	att_rect = att_rect_origin.copy()
	def_rect = def_rect_origin.copy()

	att_life_pos = (att_rect_origin.left, screen_rect.centery)
	def_life_pos = (def_rect_origin.left, screen_rect.centery)

	att_name_pos = (att_rect_origin.left, 30 + att_life_pos[1])
	def_name_pos = (def_rect_origin.left, 30 + def_life_pos[1])

	att_info_pos = (att_rect_origin.left, att_name_pos[1] + att_name.get_height() + 20)
	def_info_pos = (def_rect_origin.left, def_name_pos[1] + def_name.get_height() + 20)

	att_text_pos = (att_rect_origin.topright)
	def_text_pos = (def_rect_origin.topleft)

	life_block = pygame.Surface((4, 10))
	life_block_used = pygame.Surface((4, 10))
	life_block.fill(GREEN)
	life_block_used.fill(RED)

	collide = screen_rect.centerx, att_rect.bottom - 1
	for _round in range(at + dt + 1):
		animate_miss = False
		outcome = 0
		def_text = att_text = None
		if (at > 0 or dt > 0) and (def_swap.health > 0 and att_swap.health > 0):  # Se ci sono turni e se sono vivi
			print(" " * 6 + "-" * 6 + "Round:" + str(_round + 1) + "-" * 6)
		else:
			break
		at -= 1
		start_animation = pygame.time.get_ticks()
		animation_time = latest_tick = 0
		while animation_time < TIME_BETWEEN_ATTACKS:
			speed = int(100 / 250 * latest_tick)
			if att_swap == defending:
				speed = -speed
			if outcome == 0:
				att_rect = att_rect.move(speed, 0)
			if att_rect.collidepoint(collide) and outcome == 0:
				outcome = att_swap.attack(def_swap)
				if outcome == 1:  # Miss
					def_text = miss_text
					animate_miss = animation_time
					sounds.play('miss')
				elif outcome == 2:  # Null attack
					def_text = null_text
					sounds.play('null')
				elif outcome == 3:  # Triple hit
					att_text = crit_text
					sounds.play('critical')
				elif outcome == 4:  # Hit
					sounds.play('hit')

				att_rect = att_rect_origin.copy()
				def_rect = def_rect_origin.copy()
				#miss_target = def_rect_origin.y - 50

			if animate_miss:
				t = (animation_time - animate_miss) / 1000
				def_rect.bottom = int(att_rect.bottom - 400 * t + 800 * t * t)
				if def_rect.bottom > att_rect.bottom:
					animate_miss = False
					def_rect.bottom = att_rect.bottom

			animation_time = pygame.time.get_ticks() - start_animation

			att_info = attacking.render_info(SMALL_FONT)
			def_info = defending.render_info(SMALL_FONT)

			window.blit(battle_background, (0, 0))
			window.blit(att_swap.image, att_rect.topleft)
			window.blit(def_swap.image, def_rect.topleft)
			if att_text is not None:
				window.blit(att_text, att_text_pos)
			if def_text is not None:
				window.blit(def_text, def_text_pos)
			window.blit(att_name, att_name_pos)
			window.blit(def_name, def_name_pos)
			for i in range(attacking.health_max):
				x = att_life_pos[0] + (i % 30 * 5)
				y = att_life_pos[1] + i // 30 * 11
				if i < attacking.health:
					window.blit(life_block, (x , y))
				else:
					window.blit(life_block_used, (x , y))
			for i in range(defending.health_max):
				x = def_life_pos[0] + (i % 30 * 5)
				y = def_life_pos[1] + i // 30 * 11
				if i < defending.health:
					window.blit(life_block, (x , y))
				else:
					window.blit(life_block_used, (x , y))
			window.blit(att_info, att_info_pos)
			window.blit(def_info, def_info_pos)
			display.draw_fps()
			events.pump("Battle")
			pygame.display.flip()
			latest_tick = display.clock.tick(60)

		if dt > 0:
			att_swap, def_swap = def_swap, att_swap
			at, dt = dt, at
			att_rect, def_rect = def_rect, att_rect
			att_rect_origin, def_rect_origin = def_rect_origin, att_rect_origin
			att_text_pos, def_text_pos = def_text_pos, att_text_pos
	if attacking.health > 0:
		attacking.gain_exp(defending)
		experience_animation(attacking, battle_background)
	else:
		kill(attacking)

	if defending.health > 0:
		defending.gain_exp(attacking)
		experience_animation(defending, battle_background)
	else:
		kill(defending)

	if att_weapon and att_weapon.uses == 0:
		sounds.play('broke')
		broken_text = SMALL_FONT.render("%s is broken" % att_weapon.name, True, RED)
		window.blit(broken_text, utils.center(screen_rect, broken_text.get_rect()))
		pygame.display.flip()
		events.wait(timeout=3000, context="Battle")
	if def_weapon and def_weapon.uses == 0:
		sounds.play('broke')
		broken_text = SMALL_FONT.render("%s is broken" % def_weapon.name, True, RED)
		window.blit(broken_text, utils.center(screen_rect, broken_text.get_rect()))
		pygame.display.flip()
		events.wait(timeout=3000, context="Battle")

	pygame.mixer.music.fadeout(500)
	events.block_all()
	events.wait(500, "Battle")
	events.allow_all()
	attacking_team.play_music('map', True)

	window.blit(battle_background, (0, 0))
	attacking.played = True

	if defending_team.is_defeated():
		winner = attacking_team
	elif attacking_team.is_defeated():
		winner = defending_team

	print("#" * 12 + " " + _("Battle ends") + " " + "#" * 12 + "\r\n")


def move(who, where):
	loaded_map.move(who, where)

def play_actions(actions):
	allowed = list(events.allowed)
	pygame.time.set_timer(events.CLOCK, 0)
	for action in actions:
		action()
		events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
		events.wait(5000)
	events.set_allowed(allowed)

import action
action.Move.fun = staticmethod(move)
action.Attack.fun = staticmethod(attack)

class Sidebar(object):
	def __init__(self, font, switch_turn):
		self.rect = pygame.Rect((window.get_width() - 250, 0), (250, window.get_height()))
		self.start_time = pygame.time.get_ticks()
		self.font = font
		self.endturn_btn = gui.Button(_("End Turn"), self.font, switch_turn)

	def update(self, unit, terrain, coord, team):
		render = lambda x, y: self.font.render(x, True, y)
		self.rect.h = window.get_height()
		self.rect.x = window.get_width() - self.rect.w
		self.endturn_btn.rect.bottomright = self.rect.bottomright

		sidebar = pygame.Surface(self.rect.size)
		sidebar.fill((100, 100, 100))

		turn_s = render(_('%s phase') % team.name, team.color)
		pos = turn_s.get_rect(top=40, left=10)
		sidebar.blit(turn_s, pos)

		t_info = [
			render(terrain.name, WHITE),
			render(_("Def: %d") % terrain.defense, WHITE),
			render(_("Avoid: %d") % terrain.avoid, WHITE),
			render(_("Allowed: %s") % (", ".join(terrain.allowed)), WHITE),
		] if terrain else []

		weapon = unit.items.active if unit else None
		weapon_name = weapon.name if weapon else _("No Weapon")
		u_info = [
			render(unit.name, unit.color),
			render(weapon_name, WHITE),
		] if unit else [render(_("No unit"), WHITE)]

		delta = (pygame.time.get_ticks() - self.start_time) // 1000
		hours, remainder = divmod(delta, 3600)
		minutes, seconds = divmod(remainder, 60)

		global_info = [
			render('X: %d Y: %d' % coord, WHITE),
			render('%02d:%02d:%02d' % (hours, minutes, seconds), WHITE),
		]

		out = t_info + u_info + global_info

		for i in out:
			pos.move_ip(0, 40)
			sidebar.blit(i, pos)

		window.blit(sidebar, self.rect)
		self.endturn_btn.draw()


class SplashScreen(room.Room):
	def __init__(self):
		super().__init__()
		self.elinvention = MAIN_MENU_FONT.render("Elinvention", 1, WHITE)
		self.presents = MAIN_MENU_FONT.render(_("PRESENTS"), 1, WHITE)
		self.ticks = pygame.time.get_ticks()
		self.done = False

	def begin(self):
		resources.play_music('Beyond The Clouds (Dungeon Plunder).ogg')

	def loop(self, _events):
		return self.done

	def draw(self):
		window.fill(BLACK)
		window.blit(self.elinvention, self.elinvention.get_rect(center=window.get_rect().center))
		window.blit(self.presents, self.presents.get_rect(centery=window.get_rect().centery+MAIN_MENU_FONT.get_linesize(), centerx=window.get_rect().centerx))
		pygame.display.flip()
		events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
		events.wait(6000)
		events.allow_all()
		self.done = True


class MainMenu(room.Room):
	def __init__(self):
		super().__init__()
		self.context = "MainMenu"
		events.new_context(self.context)
		self.image = resources.load_image('Ice Emblem.png')
		self.rect = self.image.get_rect()
		self.click_to_start = MAIN_MENU_FONT.render(_("Click to Start"), 1, ICE)
		self.hmenu = gui.HorizontalMenu([(_("License"), self.show_license), (_("Settings"), self.settings_menu)], SMALL_FONT)
		self.hmenu.rect.bottomright = window.get_size()
		self.hmenu.register(self.context)
		events.bind_keys((K_RETURN, K_SPACE), events.post_interrupt, self.context)
		events.bind_click((1,), events.post_interrupt, self.hmenu.rect, False, self.context)

	def loop(self, _events):
		for event in _events:
			if event.type == events.INTERRUPT:
				return True
		return False

	def draw(self):
		window.fill(BLACK)
		self.rect.center = window.get_rect().center
		window.blit(self.image, self.rect)
		rect = self.click_to_start.get_rect(centery=window.get_rect().centery+200, centerx=window.get_rect().centerx)
		window.blit(self.click_to_start, rect)
		self.hmenu.rect.bottomright = window.get_size()
		self.hmenu.draw()

	def end(self):
		window.fill(BLACK)
		window.blit(self.image, (0, 0))

		map_menu = MapMenu(self.image)
		while not loaded_map:
			room.run_room(map_menu)

		pygame.mixer.music.fadeout(2000)
		display.fadeout(2000)
		pygame.mixer.music.stop() # Make sure mixer is not busy

	def show_license(self):
		events.new_context("License")
		gpl_image = resources.load_image('GNU GPL.jpg')
		gpl_image = pygame.transform.smoothscale(gpl_image, window.get_size())
		window.blit(gpl_image, (0, 0))
		pygame.display.flip()
		events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
		events.wait(context="License")
		events.allow_all()

	def settings_menu(self):
		room.run_room(SettingsMenu())


class SettingsMenu(room.Room):

	def __init__(self):
		super().__init__()
		self.context = "SettingsMenu"
		self.back_btn = gui.Button(_("Go Back"), MAIN_FONT, events.post_interrupt)
		self.fullscreen_btn = gui.CheckBox(_("Toggle Fullscreen"), MAIN_FONT, lambda e: display.toggle_fullscreen())

	def begin(self):
		events.new_context(self.context)
		logging.debug(_("Settings menu"))
		def res_setter(res):
			return lambda: display.set_resolution(res)
		resolutions = [("{0[0]}x{0[1]}".format(res), res_setter(res)) for res in pygame.display.list_modes()]
		self.resolutions_menu = gui.Menu(resolutions, MAIN_FONT)
		events.bind_keys((K_ESCAPE,), events.post_interrupt, self.context)
		self.back_btn.register(self.context)
		self.fullscreen_btn.register(self.context)
		self.resolutions_menu.register(self.context)

	def draw(self):
		window.fill(BLACK)
		self.back_btn.rect.bottomright = window.get_size()
		self.fullscreen_btn.rect.midtop = window.get_rect(top=50).midtop
		self.resolutions_menu.rect.midtop = window.get_rect(top=100).midtop
		self.back_btn.draw()
		self.fullscreen_btn.draw()
		self.resolutions_menu.draw()

	def loop(self, _events):
		for event in _events:
			if event.type == events.INTERRUPT:
				return True
		return False

	def kill(self, unit):
		self.map.remove_unit(unit)
		self.whose_unit(unit).units.remove(unit)

class MapMenu(room.Room):
	def __init__(self, image):
		super().__init__()
		self.context = "MapMenu"
		self.image = image
		self.rect = self.image.get_rect()
		events.new_context(self.context)
		self.files = [(f, None) for f in resources.list_maps()]
		self.choose_label = MAIN_FONT.render(_("Choose a map!"), True, ICE, MENU_BG)
		self.menu = gui.Menu(self.files, MAIN_FONT, None, (25, 25))
		self.menu.rect.center = window.get_rect().center

	def begin(self):
		events.allow_all()
		self.menu.register(self.context)

	def draw(self):
		window.fill(BLACK)
		self.rect.center = window.get_rect().center
		window.blit(self.image, self.rect)
		window.blit(self.choose_label, self.choose_label.get_rect(top=50, centerx=window.get_rect().centerx))
		self.menu.rect.center = window.get_rect().center
		self.menu.draw()

	def loop(self, _events):
		return self.menu.choice is not None

	def end(self):
		load_map(resources.map_path(self.files[self.menu.choice][0]))

class VictoryScreen(room.Room):
	def __init__(self):
		super().__init__()

	def begin(self):
		print(_("%s wins") % winner.name)
		self.victory = MAIN_MENU_FONT.render(winner.name + ' wins!', 1, winner.color)
		self.thank_you = MAIN_MENU_FONT.render(_('Thank you for playing Ice Emblem!'), 1, ICE)
		pygame.mixer.stop()
		resources.play_music('Victory Track.ogg')
		display.fadeout(1000)

	def draw(self):
		window.fill(BLACK)
		wr = window.get_rect()
		window.blit(self.victory, self.victory.get_rect(centery=wr.centery-50, centerx=wr.centerx))
		window.blit(self.thank_you, self.thank_you.get_rect(centery=wr.centery+50, centerx=wr.centerx))
		pygame.display.flip()
		pygame.event.clear()
		events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
		e = events.wait()
		print(e.type, pygame.event.event_name(e.type))

	def loop(self, events):
		return True

	def end(self):
		pygame.mixer.music.fadeout(2000)
		display.fadeout(2000)
		pygame.mixer.music.stop()


class Game(room.Room):
	def __init__(self):
		super().__init__()

	def begin(self):
		units_manager.active_team.play_music('map')
		self.sidebar = Sidebar(SMALL_FONT, self.switch_turn)
		if not units_manager.active_team.ai:
			self.enable_controls()

	def draw(self):
		window.fill(BLACK)
		loaded_map.draw(window)
		self.blit_info()

	def loop(self, _events):
		"""
		Main loop.
		"""
		self.check_turn()
		if callable(units_manager.active_team.ai):
			actions = units_manager.active_team.ai()
			play_actions(actions)
		elif loaded_map.move_x != 0 or loaded_map.move_y != 0:
			events.pump()
		else:
			# we want to wait but update the clock!
			time = pygame.time.get_ticks() - self.sidebar.start_time
			pygame.time.set_timer(events.CLOCK, (1000 - time % 1000))
			events.set_allowed([KEYDOWN, MOUSEBUTTONDOWN, MOUSEMOTION, events.CLOCK])
			events.wait()
		return winner is not None

	def end(self):
		pygame.time.set_timer(events.CLOCK, 0);

	def blit_info(self):
		coord = loaded_map.cursor.coord
		unit = loaded_map.get_unit(coord)
		terrain = loaded_map[coord]
		turn = units_manager.active_team
		self.sidebar.update(unit, terrain, coord, turn)

	def disable_controls(self):
		events.unregister(MOUSEBUTTONDOWN, self.handle_click)
		events.unregister(MOUSEMOTION, self.handle_mouse_motion)
		events.unregister(KEYDOWN, self.handle_keyboard)
		self.sidebar.endturn_btn.unregister()

	def enable_controls(self):
		events.set_allowed([KEYDOWN, MOUSEBUTTONDOWN, MOUSEMOTION, events.CLOCK])
		events.register(MOUSEBUTTONDOWN, self.handle_click)
		events.register(MOUSEMOTION, self.handle_mouse_motion)
		events.register(KEYDOWN, self.handle_keyboard)
		self.sidebar.endturn_btn.register()

	def switch_turn(self):
		active_team = units_manager.switch_turn()
		if not active_team.ai:
			self.enable_controls()
		else:
			self.disable_controls()
		loaded_map.reset_selection()
		window.fill(BLACK)
		loaded_map.draw(window)
		self.blit_info()
		phase_str = _('%s phase') % active_team.name
		phase = MAIN_MENU_FONT.render(phase_str, 1, active_team.color)
		window.blit(phase, utils.center(window.get_rect(), phase.get_rect()))
		pygame.display.flip()
		pygame.mixer.music.fadeout(1000)
		active_team.play_music('map')
		events.set_allowed([MOUSEBUTTONDOWN, KEYDOWN])
		events.wait(timeout=5000)
		events.set_allowed([KEYDOWN, MOUSEBUTTONDOWN, MOUSEMOTION, events.CLOCK])

	def action_menu(self, pos):
		"""
		Shows the action menu and handles input until it is dismissed.
		"""
		def attack():
			done = False

			def mousebuttondown(event):
				nonlocal done
				# user must click on an enemy unit
				if event.button == 1 and loaded_map.is_attack_click(event.pos):
					self.battle_wrapper(loaded_map.cursor.coord)
					done = True
				elif event.button == 3:
					loaded_map.move_undo()
					done = True

			def keydown(event):
				nonlocal done
				# user must choose an enemy unit
				if event.key == pygame.K_SPACE and loaded_map.is_enemy_cursor():
					self.battle_wrapper(loaded_map.cursor.coord)
					done = True
				elif event.key == pygame.K_ESCAPE:
					loaded_map.move_undo()
					done = True
				loaded_map.cursor.update(event)

			loaded_map.attack()
			events.new_context("Attack")
			events.register(MOUSEBUTTONDOWN, mousebuttondown, "Attack")
			events.register(KEYDOWN, keydown, "Attack")
			events.register(MOUSEMOTION, loaded_map.cursor.update, "Attack")
			def loop(_events):
				self.draw()
				display.draw_fps()
				display.flip()
				return done
			events.event_loop(loop, True, "Attack")

		def items():
			events.new_context("ItemsMenu")
			unit = loaded_map.curr_unit
			entries = [(i.name, lambda: unit.set_active(i)) for i in unit.items]
			menu = gui.Menu(entries, SMALL_FONT, loaded_map.move_undo, (5, 10), pos)
			menu.register("ItemsMenu")
			self.draw()
			room.run_room(menu)

		actions = [
			(_("Attack"), attack),
			(_("Items"), items),
			(_("Wait"), loaded_map.wait),
		] if len(loaded_map.nearby_enemies()) > 0 else [
			(_("Items"), items),
			(_("Wait"), loaded_map.wait),
		]

		events.new_context("ActionMenu")
		loaded_map.still_attack_area(loaded_map.curr_sel)
		loaded_map.update_highlight()
		loaded_map.draw(window)
		self.blit_info()

		menu = gui.Menu(actions, SMALL_FONT, loaded_map.move_undo, (5, 10), pos)
		menu.register("ActionMenu")
		events.add_allowed(gui.Menu.EVENT_TYPES)
		room.run_room(menu)

		return menu.choice

	def battle_wrapper(self, coord):
		defending = loaded_map.get_unit(coord)
		attacking = loaded_map.get_unit(loaded_map.curr_sel)

		# enemy chosen by the user... let the battle begin!
		attack(attacking, defending)

		loaded_map.reset_selection()

	def reset(self):
		pygame.mixer.fadeout(1000)
		display.fadeout(1000)
		self.done = True

	def pause_menu(self):
		events.new_context("PauseMenu")
		menu_entries = [
			('Return to Game', None),
			('Return to Main Menu', self.reset),
			('Return to O.S.', utils.return_to_os)
		]
		menu = gui.Menu(menu_entries, MAIN_FONT)
		menu.rect.center = window.get_rect().center
		menu.register("PauseMenu")
		room.run_room(menu)

	def check_turn(self):
		if units_manager.active_team.is_turn_over():
			self.switch_turn()

	def handle_mouse_motion(self, event):
		loaded_map.handle_mouse_motion(event)

	def handle_click(self, event):
		if loaded_map.handle_click(event):
			self.action_menu(event.pos)

	def handle_keyboard(self, event):
		if event.key == pygame.K_ESCAPE:
			self.pause_menu()
		else:
			if loaded_map.handle_keyboard(event):
				pos = loaded_map.tilemap.pixel_at(*loaded_map.cursor.coord)
				pos = (pos[0] + loaded_map.tilemap.tile_width, pos[1] + loaded_map.tilemap.tile_height)
				self.action_menu(pos)


def main_menu():
	room.queue_room(SplashScreen())
	room.queue_room(MainMenu())
	room.run()

def play():
	while True:
		ice = Game()
		room.queue_room(ice)
		room.queue_room(VictoryScreen())
		room.run()

