import re
import random
import cozmo
import asyncio
import sys
from cozmo.objects import CustomObjectMarkers, CustomObjectTypes
from Common.colors import Colors
from cozmo.util import degrees

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cannot import from PIL. Do `pip3 install --user Pillow` to install")


class Hangman():
    dictionary = {}
    currentPossibilities = None
    alphabetMaps = {}
    visible_things = []
    maxAttempts = 2
    correctCount = 0
    invalid_letters = 'fgypbvkjxqz'

    word = ""

    HAPPY_ANIMS = ["anim_freeplay_reacttoface_sayname_01", "anim_memorymatch_successhand_cozmo_02","anim_rtpmemorymatch_yes_01", "anim_rtpmemorymatch_yes_04"]
    SAD_ANIMS = ["anim_bored_getout_02", "anim_reacttoblock_frustrated_01"]
    WIN_ANIM = "anim_memorymatch_successhand_cozmo_04"
    LOSE_ANIM = "anim_memorymatch_failgame_cozmo_02"

    _clock_font = None
    try:
        _clock_font = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        try:
            _clock_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 22)
        except IOError:
            pass

    def __init__(self, **kwargs):
        cozmo.setup_basic_logging()
        try:
            cozmo.connect_with_tkviewer(self.run, force_on_top=True)
        except cozmo.ConnectionError as e:
            sys.exit("A connection error occurred: %s" % e)

    async def run(self, coz_conn):

        asyncio.set_event_loop(coz_conn._loop)
        self.coz = await coz_conn.wait_for_robot()



        await self.define_custom_objects();

        await self.coz.set_lift_height(0).wait_for_completed();
        await self.coz.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE / 6).wait_for_completed()
        self.exit_flag = False

        look_around = self.coz.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

        try:
            self.cubes = await self.coz.world.wait_until_observe_num_objects(3, object_type=cozmo.objects.LightCube, timeout=60)
        except asyncio.TimeoutError:
            print("Didn't find a cube :-(")
            return
        finally:
            for cube in self.cubes:
                cube.set_lights_off();
            look_around.stop()
            await self.coz.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE / 6, in_parallel=True).wait_for_completed()
            # self.cubes[0].set_lights(Colors.GREEN)
            # self.cubes[1].set_lights(Colors.RED)
            # self.cubes[2].set_lights(Colors.BLUE)

        self.gameisOn = False
        self.isGuessing = False;

        self.coz.camera.image_stream_enabled = True;
        self.coz.world.add_event_handler(cozmo.objects.EvtObjectAppeared, self.on_object_appeared)
        self.coz.world.add_event_handler(cozmo.objects.EvtObjectDisappeared, self.on_object_disappeared)
        self.coz.world.add_event_handler(cozmo.objects.EvtObjectTapped, self.on_object_tapped)

        await self.coz.turn_in_place(degrees(55)).wait_for_completed()

        while self.exit_flag is False:
            await asyncio.sleep(0)
        for cube in self.cubes:
            cube.set_lights_off();
        self.coz.abort_all_actions()

    async def on_object_tapped(self, event, *, obj, tap_count, tap_duration, **kw):
        if not self.gameisOn:
            self.gameisOn = True
            asyncio.ensure_future(self.startGame())
        elif self.isGuessing == True:
            self.isGuessing = False
            index = self.cubes.index(obj);
            if(index == 0):
                print("Correct");
                await self.got_correct_prediction(self.current_prediction)
            elif index == 1:
                print("INCORRECT");
                await self.got_incorrect_prediction(self.current_prediction);
            else:
                self.coz.abort_all_actions();
                await self.display_data(self.current_prediction.upper());
                self.isGuessing = True;
        else:
            print("going to else");

    async def on_object_appeared(self, event, *, obj, **kw):
        if 'Custom' in str(type(obj)):
            if obj not in self.visible_things:
                self.visible_things.append(obj)
        elif 'Charger' in str(type(obj)):
            if obj not in self.visible_things:
                self.visible_things.append(obj)

        self.visible_things.sort(key=lambda c: c.pose.position.y)
        word = ""
        for i in range(0, len(self.visible_things)):
            if 'Custom' in str(type(self.visible_things[i])):
                word += self.alphabetMaps[self.visible_things[i].object_type]
            elif 'Charger' in str(type(self.visible_things[i])):
                word += self.alphabetMaps['Charger']
        if self.gameisOn and len(self.word) == len(word):
            self.word = word;
        elif self.gameisOn == False:
            self.word = word;
        print("The word is " + self.word)

    async def on_object_disappeared(self, event, *, obj, **kw):
        if obj in self.visible_things:
            self.visible_things.remove(obj)

    async def startGame(self):
        await self.makeDictionary();

        # actualWord = 'toast'
        self.wordLength = len(self.word);

        self.currentPossibilities = self.dictionary[self.wordLength];
        self.wrongAttempts = 0;
        await self.guess_next_letter();

    async def guess_next_letter(self):
        self.isGuessing = True
        self.current_prediction = await self.getNextPrediction(self.wordLength, self.word);
        await self.coz.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE / 6, in_parallel=True).wait_for_completed()
        print(self.current_prediction);

        if (self.current_prediction == '.'):
            self.coz.abort_all_actions();
            self.coz.say_text("do not try to fool me!");
            print("WORD DOES NOT EXIST")
            return;
        else:
            self.coz.abort_all_actions();
            self.coz.say_text(self.current_prediction)

    async def got_incorrect_prediction(self, prediction):
        await self.TrimPossibilitiesOnLetter(prediction);
        self.wrongAttempts += 1;
        print(prediction + "," + str(self.wrongAttempts))
        if (self.wrongAttempts >= self.maxAttempts):
            print("COZMO LOST!")
            self.coz.abort_all_actions();
            await self.coz.play_anim(self.LOSE_ANIM).wait_for_completed()
        else:
            self.coz.abort_all_actions();
            await self.coz.play_anim(self.SAD_ANIMS[random.randint(0, len(self.SAD_ANIMS) - 1)]).wait_for_completed()
            numLeft = self.maxAttempts - self.wrongAttempts
            if numLeft > 1:
                await self.display_data(str(numLeft) + " tries left", 10, 6);
            else:
                await self.display_data(str(numLeft) + " try left", 10, 6);

            await asyncio.sleep(1.5);
            await self.guess_next_letter();


    async def got_correct_prediction(self, prediction):
        await self.TrimPossibilitiesOnWord(self.word, prediction)
        if ('.' not in self.word):
            print("GOT THE WORD!!!")
            self.coz.abort_all_actions();
            await self.coz.play_anim(self.WIN_ANIM).wait_for_completed()
        else:
            self.coz.abort_all_actions();
            await self.coz.play_anim(self.HAPPY_ANIMS[random.randint(0, len(self.HAPPY_ANIMS) - 1)]).wait_for_completed()
            await self.guess_next_letter();

    async def find(self, s, ch):
        return [i for i, ltr in enumerate(s) if ltr == ch]

    async def TrimPossibilitiesOnLetter(self,letter):
        newPossibilities = []
        for w in self.currentPossibilities:
            if(letter not in w):
                newPossibilities.append(w);
        self.currentPossibilities = newPossibilities;

    async def TrimPossibilitiesOnWord(self, word, letter):
        newPossibilities = []
        trueIndices = await self.find(word,letter);
        for w in self.currentPossibilities:
            matchObj = re.search(word, w, flags=0);
            indices = await self.find(w, letter);
            if (matchObj and indices == trueIndices):
                newPossibilities.append(w);
        self.currentPossibilities = newPossibilities;

    async def getNextPrediction(self, length, word):
        indices = await self.find(word,'.');
        index = indices[random.randint(0,len(indices)-1)]
        newPossibilities = []
        if (len(self.currentPossibilities) == 0):
            return '.';
        else:
            for w in self.currentPossibilities:
                matchObj = re.search(word, w, flags=0);
                if(matchObj):
                    newPossibilities.append(w);
        self.currentPossibilities = newPossibilities;
        print(self.currentPossibilities);
        return self.currentPossibilities[random.randint(0,len(self.currentPossibilities)-1)][index]

    async def makeDictionary(self):
        f = open('/usr/share/dict/words', 'r')
        str = f.read()
        arr = str.split('\n')
        for word in arr:
            if (len(word) in self.dictionary):
                obj = re.search('[fgypbvkjxqz]', word.lower())
                if(obj is None):
                    self.dictionary[len(word)].append(word.lower())
            else:
                obj = re.search('[fgypbvkjxqz]', word.lower())
                if (obj is None):
                    self.dictionary[len(word)] = [word.lower()]

    async def define_custom_objects(self):

        self.alphabetMaps[CustomObjectTypes.CustomType02] = '.';
        # self.alphabetMaps['Charger'] = 'e';
        self.alphabetMaps[CustomObjectTypes.CustomType03] = 't';
        self.alphabetMaps[CustomObjectTypes.CustomType04] = 'a';
        self.alphabetMaps[CustomObjectTypes.CustomType05] = 'o';
        self.alphabetMaps[CustomObjectTypes.CustomType06] = 'i';
        self.alphabetMaps[CustomObjectTypes.CustomType07] = 'n';
        self.alphabetMaps[CustomObjectTypes.CustomType08] = 's';
        self.alphabetMaps[CustomObjectTypes.CustomType09] = 'h';
        self.alphabetMaps[CustomObjectTypes.CustomType10] = 'r';
        self.alphabetMaps[CustomObjectTypes.CustomType11] = 'd';
        self.alphabetMaps[CustomObjectTypes.CustomType12] = 'l';
        self.alphabetMaps[CustomObjectTypes.CustomType13] = 'c';
        self.alphabetMaps[CustomObjectTypes.CustomType14] = 'u';
        self.alphabetMaps[CustomObjectTypes.CustomType15] = 'm';
        self.alphabetMaps[CustomObjectTypes.CustomType16] = 'w';
        self.alphabetMaps[CustomObjectTypes.CustomType17] = 'e';


        cube_obj_1 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType02,
                                                  CustomObjectMarkers.Diamonds2,
                                                  100,
                                                  90, 90, False)
        cube_obj_2 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType03,
                                                             CustomObjectMarkers.Diamonds3,
                                                             100,
                                                             90, 90, True)
        cube_obj_3 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType04,
                                                             CustomObjectMarkers.Diamonds4,
                                                             100,
                                                             90, 90, True)
        cube_obj_4 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType05,
                                                             CustomObjectMarkers.Diamonds5,
                                                             100,
                                                             90, 90, True)

        cube_obj_5 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType06,
                                                             CustomObjectMarkers.Circles2,
                                                             100,
                                                             90, 90, True)
        cube_obj_6 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType07,
                                                             CustomObjectMarkers.Circles3,
                                                             100,
                                                             90, 90, True)
        cube_obj_7 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType08,
                                                             CustomObjectMarkers.Circles4,
                                                             100,
                                                             90, 90, True)
        cube_obj_8 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType09,
                                                             CustomObjectMarkers.Circles5,
                                                             100,
                                                             90, 90, True)

        cube_obj_9 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType10,
                                                             CustomObjectMarkers.Triangles2,
                                                             100,
                                                             90, 90, True)
        cube_obj_10 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType11,
                                                             CustomObjectMarkers.Triangles3,
                                                             100,
                                                             90, 90, True)
        cube_obj_11 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType12,
                                                             CustomObjectMarkers.Triangles4,
                                                             100,
                                                             90, 90, True)
        cube_obj_12 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType13,
                                                             CustomObjectMarkers.Triangles5,
                                                             100,
                                                             90, 90, True)

        cube_obj_13 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType14,
                                                             CustomObjectMarkers.Hexagons2,
                                                             100,
                                                             90, 90, True)
        cube_obj_14 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType15,
                                                             CustomObjectMarkers.Hexagons3,
                                                             100,
                                                             90, 90, True)
        cube_obj_15 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType16,
                                                             CustomObjectMarkers.Hexagons4,
                                                             100,
                                                             90, 90, True)
        cube_obj_16 = await self.coz.world.define_custom_cube(CustomObjectTypes.CustomType17,
                                                             CustomObjectMarkers.Hexagons5,
                                                             100,
                                                             90, 90, True)

    async def display_data(self,text, offsetX = 60, offsetY = 6):
        self.coz.abort_all_actions();
        clock_image = self.make_text_image(text, offsetX, offsetY, self._clock_font)
        oled_face_data = cozmo.oled_face.convert_image_to_screen_data(clock_image)

        # display for 1 second
        self.coz.display_oled_face_image(oled_face_data, 2000.0)

    def make_text_image(self, text_to_draw, x, y, font=None):

        # make a blank image for the text, initialized to opaque black
        text_image = Image.new('RGBA', cozmo.oled_face.dimensions(), (0, 0, 0, 255))

        # get a drawing context
        dc = ImageDraw.Draw(text_image)

        font
        # draw the text
        dc.text((x, y), text_to_draw, fill=(255, 255, 255, 255), font=font)

        return text_image
if __name__ == '__main__':
    Hangman();
