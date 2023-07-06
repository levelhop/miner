import random
import time
from model.osrs.WillowsDad.WillowsDad_bot import WillowsDadBot
import utilities.api.item_ids as ids
import utilities.api.animation_ids as animation
import utilities.color as clr
import utilities.random_util as rd
import utilities.imagesearch as imsearch
import pyautogui as pag
from utilities.geometry import RuneLiteObject
import utilities.game_launcher as launcher
from pathlib import Path
import threading





class OSRSWDMining(WillowsDadBot):
    def __init__(self):
        bot_title = "WD Mining"
        description = """Mines at supported locations."""
        super().__init__(bot_title=bot_title, description=description)
        # Set option variables below (initial value is only used during UI-less testing)
        self.running_time = 200
        self.take_breaks = True
        self.afk_train = True
        self.delay_min =0.37
        self.delay_max = .67
        self.ores = ids.ores
        self.power_Mining = False
        self.Mining_tools = ids.pickaxes
        self.dragon_special = False
        self.location = "Mining Guild"


    def create_options(self):
        """
        Use the OptionsBuilder to define the options for the bot. For each function call below,
        we define the type of option we want to create, its key, a label for the option that the user will
        see, and the possible values the user can select. The key is used in the save_options function to
        unpack the dictionary of options after the user has selected them.
        """
        super().create_options()
        self.options_builder.add_checkbox_option("power_Mining", "Power Mining? Drops everything in inventory.", [" "])
        self.options_builder.add_checkbox_option("dragon_special", "Use Dragon Pickaxe Special?", [" "])
        self.options_builder.add_checkbox_option("location", "Location?", ["Varrock East","Mining Guild"])

    def save_options(self, options: dict):
        """
        For each option in the dictionary, if it is an expected option, save the value as a property of the bot.
        If any unexpected options are found, log a warning. If an option is missing, set the options_set flag to
        False.
        """
        super().save_options(options)
        for option in options:
            if option == "power_Mining":
                self.power_Mining = options[option] != []
            elif option == "dragon_special":
                self.dragon_special = options[option] != []
            elif option == "location":
                self.location = options[option]
            else:
                self.log_msg(f"Unexpected option: {option}")

        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Bot will{'' if self.take_breaks else ' not'} take breaks.")
        self.log_msg(f"Bot will{'' if self.afk_train else ' not'} train like you're afk on another tab.")
        self.log_msg(f"Bot will wait between {self.delay_min} and {self.delay_max} seconds between actions.")
        self.log_msg(f"Bot will{'' if self.power_Mining else ' not'} power mine.")
        self.log_msg("Options set successfully.")
        self.options_set = True


    def launch_game(self):
    
        # If playing RSPS, change `RuneLite` to the name of your game
        if launcher.is_program_running("RuneLite"):
            self.log_msg("RuneLite is already running. Please close it and try again.")
            return
        
        settings = Path(__file__).parent.joinpath("WDMiner.properties")
        launcher.launch_runelite(
            properties_path=settings, 
            game_title=self.game_title, 
            use_profile_manager=True, 
            profile_name="WDMiner", 
            callback=self.log_msg)

    def main_loop(self):
        """
        Main bot loop. We call setup() to set up the bot, then loop until the end time is reached.
        """
        # Setup variables
        self.setup()
        # Main loop
        while time.time() - self.start_time < self.end_time:

            runtime = int(time.time() - self.start_time)
            minutes_since_last_break = int((time.time() - self.last_break) / 60)
            seconds = int(time.time() - self.last_break) % 60
            percentage = (self.multiplier * .01)  # this is the percentage chance of a break
            deposit_slots = self.api_m.get_first_occurrence(self.deposit_ids)
            self.roll_chance_passed = False

            try:
                while not self.is_inv_full():
                    if self.api_m.get_run_energy() == 10000:
                        run = imsearch.search_img_in_rect(self.WILLOWSDAD_IMAGES.joinpath("run_enabled.png"),
                                                        self.win.run_orb.scale(3, 3))
                        if run is None:
                            self.mouse.move_to(self.win.run_orb.random_point())
                            self.mouse.click()
                            time.sleep(self.random_sleep_length())

                    # Check if mining spot is available in the desired order
                    for color in [clr.BLUE, clr.GREEN, clr.PINK]:
                        if Mining_spot := self.get_nearest_tag(color):
                            self.go_mining()
                            deposit_slots = self.api_m.get_first_occurrence(self.deposit_ids)
                            break


                if not self.power_Mining:
                    self.bank_or_drop()
                    self.check_equipment()
                    self.walk_to_mine()

                else:
                    self.bank_or_drop(deposit_slots)


            except Exception as e:
                self.log_msg(f"Exception: {e}")
                self.loop_count += 1
                if self.loop_count > 5:
                    self.log_msg("Too many exceptions, stopping.")
                    self.log_msg(f"Last exception: {e}")
                    self.stop()
                continue


            # -- End bot actions --
            self.loop_count = 0
            if self.take_breaks:
                self.check_break(runtime, percentage, minutes_since_last_break, seconds)
            current_progress = round((time.time() - self.start_time) / self.end_time, 2)
            if current_progress != round(self.last_progress, 2):
                self.update_progress((time.time() - self.start_time) / self.end_time)
                self.last_progress = round(self.progress, 2)

        self.update_progress(1)
        self.log_msg("Finished.")
        self.logout()
        self.stop()
    
    
    def setup(self):
        """Sets up loop variables, checks for required items, and checks location.
            This will ideally stop the bot from running if it's not setup correctly.
            * To-do: Add functions to check for required items, bank setup and locaiton.
            Args:
                None
            Returns:
                None"""
        super().setup()
        self.idle_time = 0
        self.deposit_ids = self.ores
        self.deposit_ids.extend([ids.UNCUT_DIAMOND, ids.UNCUT_DRAGONSTONE, ids.UNCUT_EMERALD, ids.UNCUT_RUBY, ids.UNCUT_SAPPHIRE, ids.UNIDENTIFIED_MINERALS])


        # Setup Checks for pickaxes and tagged objects
        self.check_equipment()

        if not self.get_nearest_tag(clr.YELLOW) and not self.get_nearest_tag(clr.PINK) and not self.power_Mining and not self.get_nearest_tag(clr.CYAN):
            self.log_msg("Did not see a bank(YELLOW) or a Mining spot (PINK) on screen, or a tile (CYAN) make sure they are tagged.")
            self.adjust_camera(clr.YELLOW)
            self.stop()
        if not self.get_nearest_tag(clr.CYAN) and not self.power_Mining:
            self.log_msg("Did not see any tiles tagged CYAN, make sure they are tagged so I can get back in position.")
            self.stop()



    def go_mining(self):
        self.breaks_skipped = 0
        afk_time = 0
        afk_start_time = time.time()
    
        self.is_runelite_focused()
        if not self.is_focused:
            self.log_msg("Runelite is not focused...")
        
        colors = [clr.BLUE, clr.GREEN, clr.PINK]
        last_mined_index = -1
        exhausted_colors = set()
    
        while not self.is_inv_full():
            if self.get_special_energy() >= 100 and self.dragon_special:
                self.activate_special()
                self.log_msg("Dragon Pickaxe Special Activated")
    
            self.idle_time = time.time()
            afk_time = int(time.time() - afk_start_time)
    
            for i in range(last_mined_index + 1, len(colors)):
                color = colors[i]
                if color in exhausted_colors:
                    continue
    
                mining_spot = self.get_nearest_tag(color)
                if mining_spot:
                    self.mouse.move_to(mining_spot.random_point(), mouseSpeed="fast")
                    next_mining_spot = None
                    while not self.mouse.click(check_red_click=True):
                        if next_mining_spot is None:
                            next_color_index = (i + 1) % len(colors)
                            next_color = colors[next_color_index]
                            next_mining_spot = self.get_nearest_tag(next_color)
                            if next_mining_spot:
                                self.mouse.move_to(next_mining_spot.random_point(), mouseSpeed="fast")
                        mining_spot = self.get_nearest_tag(color)
                        if mining_spot:
                            self.mouse.move_to(mining_spot.random_point(), mouseSpeed="fast")
                    
                    while self.get_nearest_tag(color):  # Continuously check if the color is still present
                        if next_mining_spot is None:
                            next_color_index = (i + 1) % len(colors)
                            next_color = colors[next_color_index]
                            next_mining_spot = self.get_nearest_tag(next_color)
                            if next_mining_spot:
                                self.mouse.move_to(next_mining_spot.random_point(), mouseSpeed="fast")
                        time.sleep(self.random_sleep_length(0.01, 0.03))  # Adjust sleep time as needed
                    
                    last_mined_index = i
                    exhausted_colors.clear()  # Reset exhausted colors
                    break
                else:
                    exhausted_colors.add(color)
    
            if last_mined_index == -1 or last_mined_index == len(colors) - 1:
                exhausted_colors.clear()  # Reset exhausted colors
                last_mined_index = -1
        
        self.breaks_skipped = afk_time // 15
    
        if self.breaks_skipped > 0:
            self.roll_chance_passed = True
            self.multiplier += self.breaks_skipped * 0.25
            self.log_msg(f"Skipped {self.breaks_skipped} break rolls while mining.")


    def handle_no_mining_spot(self):
        # Define constants at the top of your script
        IDLE_TIME_LIMIT_1 = 10
        IDLE_TIME_LIMIT_2 = 32
        IDLE_TIME_LIMIT_3 = 60
        
        idle_time_elapsed = int(time.time() - self.idle_time)
        if idle_time_elapsed > IDLE_TIME_LIMIT_1:
            if self.get_nearest_tag(clr.CYAN):
                self.mouse.move_to(self.get_nearest_tag(clr.CYAN).random_point())
                self.mouse.click()
            time.sleep(self.random_sleep_length())
        if idle_time_elapsed > IDLE_TIME_LIMIT_2:
            self.adjust_camera(clr.BLUE, 1)
        if idle_time_elapsed > IDLE_TIME_LIMIT_3:
            self.log_msg("No Mining spot found in 60 seconds, quitting bot.")
            self.stop()

    def click_deposit(self):
        # While Deposit is not in text, move mouse.
        deposit_all_img = self.WILLOWSDAD_IMAGES.joinpath("bank_all.png")
        tries = 0
        while not self.mouseover_text(contains="inventory"):
            # Stop after 5 tries
            if tries > 5:
                self.log_msg('Failed to continue, stopping')
                return False
            
            
            if deposit_all := imsearch.search_img_in_rect(deposit_all_img, self.win.game_view):
                # Found image
                self.mouse.move_to(deposit_all.random_point(), mouseSpeed = "fast")
            else:
                self.log_msg('Failed to find deposit all')
                tries = tries + 1
                continue

        # Click to deposit
        self.mouse.click()

    def bank_or_drop(self):
        """
        This will either bank or drop items depending on the power_Mining setting.
        Returns: void
        Args: None"""
        if not self.power_Mining:
            self.open_bank()
            time.sleep(self.random_sleep_length()/2)
            self.click_deposit()
            time.sleep(self.random_sleep_length()/2)
            self.close_bank()
        else:
            self.drop_all(skip_slots=self.api_m.get_inv_item_indices(self.Mining_tools))

    def check_equipment(self):
        """
        Stops script if no axe is equipped.
        Returns: none
        Args: None
        """
        if not self.api_m.get_if_item_in_inv(self.Mining_tools) and not self.api_m.get_is_item_equipped(self.Mining_tools):
            self.log_msg("No Mining tool or in inventory, please fix that...")
            self.stop()
    
    def walk_to_mine(self):
        """
        If cyan tiles are on screen and not clicked then randomly choose tile to click.
        Returns: none
        Args: None
        """
        shape_click= False
        shapes = self.get_all_tagged_in_rect(self.win.game_view, clr.CYAN)
        
        if shapes and not shape_click:
            random_tile = random.choice(shapes)
            self.mouse.move_to(random_tile.random_point(), mouseSpeed = "fast")
            self.mouse.click()
            time.sleep(self.random_sleep_length(4.5, 5.24))
