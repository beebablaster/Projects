import pygame as pg
import os
import pika
import uuid
import json
from threading import Thread

_image_library = {}
def get_image(path):
        global _image_library
        image = _image_library.get(path)
        if image == None:
                canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
                image = pg.image.load(canonicalized_path)
                _image_library[path] = image
        return image

class RPCConsumer(Thread):
    def __init__(self, binding_key):
        Thread.__init__(self)
        self.binding_key = binding_key
        self.cb = None
        self.corr_id = None
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('34.254.177.17', 5672, 'dar-tanks', pika.PlainCredentials('dar-tanks', '5orPLExUYnyVYZg48caMpX')))
        self.channel = self.connection.channel()
        self.channel.queue_declare(self.binding_key, exclusive=True)
        self.channel.queue_bind(exchange='X:routing.topic',
                                queue=self.binding_key, routing_key=self.binding_key)
    def run(self):
        def callback(ch, method, props, body):
            if self.corr_id == props.correlation_id:
                self.response = body
                decoded = body.decode('utf-8') # decoded string

                if self.cb is not None:
                    self.cb(decoded)
            else:
                print("{}".format(body))

        self.channel.basic_consume(queue=self.binding_key, on_message_callback=callback, auto_ack=True)
        print("Starting RPC consumer")
        self.connection.process_data_events()
        self.channel.start_consuming() # blocks thread

    def set_callback(self, corr_id, cb):
        self.corr_id = corr_id
        self.cb = cb

class RPCClient(Thread):
    def __init__(self, queue_name, rpc_consumer):
        Thread.__init__(self)
        self.rpc_consumer = rpc_consumer
        self.queue_name = queue_name
        self.exchange = 'X:routing.topic'
        self.corr_id = None
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('34.254.177.17', 5672, 'dar-tanks', pika.PlainCredentials('dar-tanks', '5orPLExUYnyVYZg48caMpX')))
        self.channel = self.connection.channel()

    def run(self) -> None:
        pass

    def call(self, request, rk, cb):
        self.corr_id = str(uuid.uuid4())
        self.rpc_consumer.set_callback(self.corr_id, cb)

        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=rk,
            properties=pika.BasicProperties(
                reply_to=self.queue_name,
                correlation_id=self.corr_id

            ),
            body=str(request)
        )


class RoomState(Thread):
    def __init__(self):
        Thread.__init__(self)

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('34.254.177.17', 5672, 'dar-tanks',
                                      pika.PlainCredentials('dar-tanks', '5orPLExUYnyVYZg48caMpX')))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='X:routing.topic', exchange_type='topic', durable=True)

        self.result = self.channel.queue_declare('', auto_delete=True, exclusive=True)
        self.queue_name = self.result.method.queue

        self.channel.queue_bind(
            exchange='X:routing.topic', queue=self.queue_name, routing_key='event.state.room-5')

    def run(self):
        def callback(ch, method, properties, body):
            global state
            state = json.loads(body)

        self.channel.basic_consume(
            queue=self.queue_name, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()

def handle_direction_response(body):
    print(f'Received direction response: {body}')


def handle_register_response(body):
    print(f'Received register response: {body}')
    t = json.loads(body)
    global token
    token = t["token"]
    global tankid
    tankid = t["tankId"]


def handle_fire_response(body):
    print(f'Received fire response: {body}')

queue_name = "{}.response".format(uuid.uuid4())
rpc_consumer = RPCConsumer(queue_name)
rpc_consumer.daemon = True
rpc_consumer.start()

rpc_client = RPCClient(queue_name, rpc_consumer)
rpc_client.daemon = True
rpc_client.start()

a = {"roomId":"room-15"}
b =json.dumps(a)
rpc_client.call(b,'tank.request.register', handle_register_response)
room_state=RoomState()
room_state.daemon = True
room_state.start()

class SceneParent:
    def __init__(self):
        self.next = self

    def ProcessInput(self, events, pressed_keys):
        print("uh-oh, you didn't override this in the child class")

    def Update(self):
        print("uh-oh, you didn't override this in the child class")

    def Render(self, screen):
        print("uh-oh, you didn't override this in the child class")

    def SwitchToScene(self, next_scene):
        self.next = next_scene

    def Terminate(self):
        self.SwitchToScene(None)


def launch(width, height, fps, starting_scene):
    pg.init()

    screen = pg.display.set_mode((width, height))
    clock = pg.time.Clock()

    active_scene = starting_scene

    while active_scene != None:
        pressed_keys = pg.key.get_pressed()
        # Event filtering
        filtered_events = []
        for event in pg.event.get():
            quit_attempt = False
            if event.type == pg.QUIT:
                quit_attempt = True
            elif event.type == pg.KEYDOWN:
                alt_pressed = pressed_keys[pg.K_LALT] or \
                              pressed_keys[pg.K_RALT]
                if event.key == pg.K_ESCAPE:
                    quit_attempt = True
                elif event.key == pg.K_F4 and alt_pressed:
                    quit_attempt = True

            if quit_attempt:
                active_scene.Terminate()
            else:
                filtered_events.append(event)

        active_scene.ProcessInput(filtered_events, pressed_keys)
        active_scene.Update()
        active_scene.Render(screen)
        active_scene = active_scene.next

        pg.display.flip()
        clock.tick(fps)


class MainMenu(SceneParent):
    pg.init()

    def __init__(self):
        SceneParent.__init__(self)
        pg.mixer.music.load('./l/menutheme.mp3')
        pg.mixer.music.play(0)

    def write(self, msg="pygame is cool"):
        myfont = pg.font.Font("./l/Pixeboy-z8XGD.ttf", 40)
        mytext = myfont.render(msg, True, (111, 3, 252))
        mytext = mytext.convert_alpha()
        return mytext

    def ProcessInput(self, events, pressed_keys):
        for event in events:
            self.x = pg.mouse.get_pos()
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1 and (self.x[0] >= 10 and self.x[0] <= 10 + self.button1.size[0]) and (
                        self.x[1] >= 240 and self.x[1] <= 240 + self.button1.size[1]):
                    self.SwitchToScene(GameField())

                if event.button == 1 and (self.x[0] >= 10 and self.x[0] <= 10 + self.button1.size[0]) and (
                        self.x[1] >= 170 and self.x[1] <= 170 + self.button1.size[1]):
                    self.SwitchToScene(GameFieldSingle())

        if pressed_keys[pg.K_m]:
            self.SwitchToScene(GameField())
    def Update(self):
        pass

    def Render(self, screen):
        self.screen = screen
        screen.blit(get_image('./l/m.jpg'), (0, 0))
        textsur1 = self.write('Single Player')
        textsur2 = self.write('Multiplayer')
        textsur3 = self.write('Multiplayer(AI)')
        textsur4 = self.write('TANKS  by  BEEBABLASTER ')
        textsur5 = self.write('CHOOSE GAME MODE:')
        self.button1 = screen.blit(textsur1, (10, 170))
        self.button2 = screen.blit(textsur2, (10, 240))
        self.button3 = screen.blit(textsur3, (10, 300))
        self.title = screen.blit(textsur4, (290, 10))
        self.choose = screen.blit(textsur5, (30, 100))
        if (self.x[0] >= 10 and self.x[0] <= 10 + self.button1.size[0]) and (
                self.x[1] >= 170 and self.x[1] <= 170 + self.button1.size[1]):
            pg.draw.rect(screen, (255, 255, 255),
                             pg.Rect(0, 180 + self.button1.size[1], self.button1.size[0], 3))
        if (self.x[0] >= 10 and self.x[0] <= 10 + self.button2.size[0]) and (
                self.x[1] >= 240 and self.x[1] <= 240 + self.button2.size[1]):
            pg.draw.rect(screen, (255, 255, 255),
                             pg.Rect(0, 250 + self.button2.size[1], self.button2.size[0], 3))
        if (self.x[0] >= 10 and self.x[0] <= 10 + self.button3.size[0]) and (
                self.x[1] >= 300 and self.x[1] <= 300 + self.button3.size[1]):
            pg.draw.rect(screen, (255, 255, 255),
                             pg.Rect(0, 310 + self.button3.size[1], self.button3.size[0], 3))


class Tank:
    def __init__(self, originX, originY, speed):
        self.originX = originX
        self.originY = originY
        self.angle = 0
        self.speed = speed
        self.direction = "UP"
        self.Health = 3
        self.time = 0
        self.time2 = 3146

    def ChangeDirection(self, direction):
        self.direction = direction

    def UpdateLocation(self, seconds):
        if self.direction == "UP":
            self.originY -= self.speed * seconds
            if self.originY < 0:
                self.originY = 600
        elif self.direction == "RIGHT":
            self.originX += self.speed * seconds
            if self.originX > 800:
                self.originX = 0
        elif self.direction == "DOWN":
            self.originY += self.speed * seconds
            if self.originY > 600:
                self.originY = 0
        elif self.direction == "LEFT":
            self.originX -= self.speed * seconds
            if self.originX < 0:
                self.originX = 800

    def GetCorpus(self, image):
        corpus = get_image(image)
        newcorp = pg.transform.scale(corpus, (31, 31))
        centerT = newcorp.get_rect(center=(self.originX, self.originY))
        rc = pg.transform.rotate(newcorp, self.angle)
        nc = rc.get_rect(center=centerT.center)
        return rc, nc

    def GetDulo(self, image):
        dulo = get_image(image)
        newdulo = pg.transform.scale(dulo, (50, 50))
        centerD = newdulo.get_rect(center=(self.originX, self.originY))
        rd = pg.transform.rotate(newdulo, self.angle)
        nc = rd.get_rect(center=centerD.center)
        return rd, nc


class Bullet:
    def __init__(self, bulletX, bulletY, angleB):
        self.bulletX = bulletX
        self.bulletY = bulletY
        self.direction = 0
        self.speed = 9
        self.angle = angleB

    def ChangeDirection(self, direction):
        self.direction = direction

    def UpdateLocation(self):
        if self.direction == "UP":
            self.bulletY -= self.speed
            if (self.bulletY < -20):
                self.direction = 0
                self.bulletX = -1020
        elif self.direction == "RIGHT":
            self.bulletX += self.speed
            if (self.bulletX > 1020):
                self.direction = 0
                self.bulletX = -1020
        elif self.direction == "DOWN":
            self.bulletY += self.speed
            if (self.bulletY > 1020):
                self.direction = 0
                self.bulletX = -1020
        elif self.direction == "LEFT":
            self.bulletX -= self.speed
            if (self.bulletX < -20):
                self.direction = 0
                self.bulletX = -1020

    def GetBullet(self):
        shot = get_image('./l/pullet.png')
        newshot = pg.transform.scale(shot, (5, 15))
        centerS = newshot.get_rect(center=(self.bulletX, self.bulletY))
        rs = pg.transform.rotate(newshot, self.angle)
        nc = rs.get_rect(center=centerS.center)
        return (rs, nc)

class GameFieldSingle(SceneParent):
    def __init__(self):
        SceneParent.__init__(self)
        self.tank1 = Tank(123, 123, 1)
        self.bullet1 = Bullet(-1020, -100, 0)

    def ProcessInput(self, events, pressed_keys):
        if pressed_keys[pg.K_w]:
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.ChangeDirection("UP")
            self.tank1.angle = 0 % 360
            self.bullet1.angle = 0 % 360


        if pressed_keys[pg.K_d]:
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.ChangeDirection("RIGHT")
            self.tank1.angle = 270 % 360
            self.bullet1.angle = 270 % 360

        if pressed_keys[pg.K_s]:
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.ChangeDirection("DOWN")
            self.tank1.angle = 180 % 360
            self.bullet1.angle = 180 % 360


        if pressed_keys[pg.K_a]:
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.ChangeDirection("LEFT")
            self.tank1.angle = 90 % 360
            self.bullet1.angle = 90 % 360

        if pressed_keys[pg.K_BACKSPACE]:
            self.tank1.ChangeDirection(0)

        if pressed_keys[pg.K_SPACE]:
                self.tank1.time = 0
                pg.mixer.music.load('./l/missile.mp3')
                pg.mixer.music.play(0)
                self.bullet1.bulletX = self.tank1.originX
                self.bullet1.bulletY = self.tank1.originY
                if self.tank1.direction == "UP":
                    self.bullet1.ChangeDirection("UP")
                if self.tank1.direction == "RIGHT":
                    self.bullet1.ChangeDirection("RIGHT")
                if self.tank1.direction == "DOWN":
                    self.bullet1.ChangeDirection("DOWN")
                if self.tank1.direction == "LEFT":
                    self.bullet1.ChangeDirection("LEFT")

    def Update(self):
        self.bullet1.UpdateLocation()
        self.tank1.UpdateLocation(0.5)

    def write(self, msg="pygame is cool"):
        myfont = pg.font.Font("./l/Pixeboy-z8XGD.ttf", 35)
        mytext = myfont.render(msg, True, (255, 255, 255))
        mytext = mytext.convert_alpha()
        return mytext

    def Render(self, screen):
        screen.blit(get_image('./l/mem.jpg'), (0, 0))
        screen.blit(self.tank1.GetCorpus('./l/morpus.png')[0],
                    self.tank1.GetCorpus('./l/morpus.png')[1])
        screen.blit(self.tank1.GetDulo('./l/mulo.png')[0],
                    self.tank1.GetDulo('./l/mulo.png')[1])
        x = self.bullet1.GetBullet()
        screen.blit(x[0], x[1])
        pg.display.set_caption("Tanks")
        pg.draw.rect(screen, (46, 21, 130), (0, 600, 1000, 200), 8)
        pg.draw.rect(screen, (46, 21, 130), (800, 0, 200, 800), 8)
        pg.draw.rect(screen, (0, 0, 0), (8, 603, 792, 200), 0)
        pg.draw.rect(screen, (0, 0, 0), (803, 0, 190, 600), 0)
        text = self.write("SINGLEPLAYER")
        screen.blit(text, (805, 700))


class GameField(SceneParent):
    def __init__(self):
        SceneParent.__init__(self)
        self.tank1 = Tank(123, 123, 1)
        self.bullet1 = Bullet(-820, -80, 0)


    def ProcessInput(self, events, pressed_keys):
        if pressed_keys[pg.K_w]:
            message = {"token": f'{token}', "direction": "UP"}
            y = json.dumps(message)
            rpc_client.call(y, 'tank.request.turn', handle_direction_response)
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)

            self.tank1.angle = 0 % 360
            self.bullet1.angle = 0 % 360

        if pressed_keys[pg.K_d]:
            message = {"token": f'{token}', "direction": "RIGHT"}
            y = json.dumps(message)
            rpc_client.call(y, 'tank.request.turn', handle_direction_response)
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)

            self.tank1.angle = 270 % 360
            self.bullet1.angle = 270 % 360

        if pressed_keys[pg.K_s]:
            message = {"token": f'{token}', "direction": "DOWN"}
            y = json.dumps(message)
            rpc_client.call(y, 'tank.request.turn', handle_direction_response)
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.angle = 180 % 360
            self.bullet1.angle = 180 % 360

        if pressed_keys[pg.K_a]:
            message = {"token": f'{token}', "direction": "LEFT"}
            y = json.dumps(message)
            rpc_client.call(y, 'tank.request.turn', handle_direction_response)
            pg.mixer.music.load('./l/move.mp3')
            pg.mixer.music.play(0)
            self.tank1.angle = 90 % 360
            self.bullet1.angle = 90 % 360

        if pressed_keys[pg.K_BACKSPACE]:
            self.tank1.ChangeDirection(0)

        if pressed_keys[pg.K_SPACE]:
            message = {"token": f'{token}'}
            y = json.dumps(message)
            rpc_client.call(y, 'tank.request.fire', handle_fire_response)
            self.tank1.time = 0
            pg.mixer.music.load('./l/missile.mp3')
            pg.mixer.music.play(0)
            self.bullet1.bulletX = self.tank1.originX
            self.bullet1.bulletY = self.tank1.originY
            if self.tank1.direction == "UP":
                self.bullet1.ChangeDirection(1)
            if self.tank1.direction == "RIGHT":
                self.bullet1.ChangeDirection(2)
            if self.tank1.direction == "DOWN":
                self.bullet1.ChangeDirection(3)
            if self.tank1.direction == "LEFT":
                self.bullet1.ChangeDirection(4)

    def Update(self):
        self.bullet1.UpdateLocation()


    def write(self, msg="pygame is cool"):
        myfont = pg.font.Font("./l/Pixeboy-z8XGD.ttf", 35)
        mytext = myfont.render(msg, True, (255, 255, 255))
        mytext = mytext.convert_alpha()
        return mytext

    def Render(self, screen):
        screen.blit(get_image('./l/mem.jpg'), (0, 0))
        for i in state["gameField"]["tanks"]:
            t = [int(i["x"]), int(i["y"])]
            if i["id"] == tankid:
                self.tank1 = Tank(t[0] + 15, t[1] + 15, 1)

                if i["direction"] == "UP":
                    self.tank1.angle = 0 % 360
                    self.bullet1.angle = 0 % 360
                if i["direction"] == "DOWN":
                    self.tank1.angle = 180 % 360
                    self.bullet1.angle = 180 % 360
                if i["direction"] == "LEFT":
                    self.tank1.angle = 90 % 360
                    self.bullet1.angle = 90 % 360
                if i["direction"] == "RIGHT":
                    self.tank1.angle = 270 % 360
                    self.bullet1.angle = 270 % 360
                screen.blit(self.tank1.GetCorpus('./l/morpus.png')[0],
                            self.tank1.GetCorpus('./l/morpus.png')[1])
                screen.blit(self.tank1.GetDulo('./l/mulo.png')[0],
                            self.tank1.GetDulo('./l/mulo.png')[1])

            if i["id"] != tankid:
                i["width"] = Tank(t[0] + 15, t[1] + 15, 1)
                if i["direction"] == "UP":
                    i["width"].angle = 0 % 360
                if i["direction"] == "DOWN":
                    i["width"].angle = 180 % 360
                if i["direction"] == "LEFT":
                    i["width"].angle = 90 % 360
                if i["direction"] == "RIGHT":
                    i["width"].angle = 270 % 360
                screen.blit(i["width"].GetCorpus('./l/enemycorpus.png')[0],
                            i["width"].GetCorpus('./l/enemycorpus.png')[1])
                screen.blit(i["width"].GetDulo('./l/enemydulo.png')[0],
                            i["width"].GetDulo('./l/enemydulo.png')[1])

        pg.draw.rect(screen, (46, 21, 130), (0, 600, 1000, 200), 8)
        pg.draw.rect(screen, (46, 21, 130), (800, 0, 200, 800), 8)
        pg.draw.rect(screen, (0,0,0), (8, 603, 792, 200), 0)
        pg.draw.rect(screen, (0,0,0), (803, 0, 190, 600), 0)

        for i in state["gameField"]["bullets"]:
            t = [int(i["x"]), int(i["y"])]
            if i["owner"] == tankid:
                self.bullet1.bulletX = i["x"]
                self.bullet1.bulletY = i["y"]
                if i["direction"] == "UP":
                    self.bullet1.angle = 0 % 360
                if i["direction"] == "DOWN":
                    self.bullet1.angle = 180 % 360
                if i["direction"] == "LEFT":
                    self.bullet1.angle = 90 % 360
                if i["direction"] == "RIGHT":
                    self.bullet1.angle = 270 % 360
                x1 = self.bullet1.GetBullet()
                screen.blit(x1[0], x1[1])
                y1 = self.bullet1.GetBullet()
                screen.blit(y1[0], y1[1])

            if i["owner"] != tankid:
                i["owner"] = Bullet(t[0] + 15, t[1] + 15, 0)
                if i["direction"] == "UP":
                    i["owner"].angle = 0 % 360
                if i["direction"] == "DOWN":
                    i["owner"].angle = 180 % 360
                if i["direction"] == "LEFT":
                    i["owner"].angle = 90 % 360
                if i["direction"] == "RIGHT":
                    i["owner"].angle = 270 % 360
                a = i["owner"].GetBullet()
                screen.blit(a[0], a[1])
                b = i["owner"].GetBullet()
                screen.blit(b[0], b[1])
        idcount = 0

        for i in state["gameField"]["tanks"]:
            if i["id"] == tankid:
                textsurface1 = self.write(f'Health: {i["health"]}')
                textsurface2 = self.write(f'Score: {i["score"]}')
                textsurface3 = self.write("MY TANK:")
                textsurface4 = self.write(f'ID : {tankid}')
                screen.blit(textsurface3,(820,60))
                screen.blit(textsurface1, (810, 100))
                screen.blit(textsurface2, (810, 150))
                screen.blit(textsurface4, (805, 200))
            if i["id"] != tankid:
                    idcount += 1
                    b = 30
                    textsurface1 = self.write(f'P : {i["id"]}       SCORE : {i["score"]}       HEALTH : {i["health"]}')
                    screen.blit(textsurface1, (10, 590 + idcount*b))

        for i in state["hits"]:
            if i["destination"] == tankid:
                pg.mixer.music.load('./l/movie.mp3')
                pg.mixer.music.play(0)
            if i["source"] == tankid:
                pg.mixer.music.load('./l/movie.mp3')
                pg.mixer.music.play(0)

        for i in state["winners"]:
            if i["tankId"] == tankid:
                pg.mixer.music.load('./l/w.mp3')
                pg.mixer.music.play(0)
                self.SwitchToScene(GGScene())

        for i in state["losers"]:
            if i["tankId"] == tankid:
                pg.mixer.music.load('./l/lose.mp3')
                pg.mixer.music.play(0)
                self.SwitchToScene(WPScene())




        pg.display.set_caption("Tanks")
        textsurface3 = self.write(f'Time: {state["remainingTime"]}')
        screen.blit(textsurface3, (440, 0))

        text = self.write("MULTIPLAYER")
        screen.blit(text,(810,700))


class GGScene(GameField):
    def __init__(self):
        GameField.__init__(self)

    def ProcessInput(self, events, pressed_keys):
        for event in events:
            if event.type == pg.KEYDOWN and event.key == pg.K_x:
                self.SwitchToScene(GameField())

    def Update(self):
        pass

    def write(self, msg="pygame is cool"):
        myfont = pg.font.Font("./l/Pixeboy-z8XGD.ttf", 100)
        mytext = myfont.render(msg, True, (0, 0, 0))
        mytext = mytext.convert_alpha()
        return mytext

    def Render(self, screen):
        screen.blit(get_image('./l/win.jpg'), (0, 0))
        textsurface1 = self.write('Tank №1 WINS! GG!')
        screen.blit(textsurface1, (280, 400))


class WPScene(GameField):
    def __init__(self):
        GameField.__init__(self)

    def ProcessInput(self, events, pressed_keys):
        for event in events:
            if event.type == pg.KEYDOWN and event.key == pg.K_x:
                self.SwitchToScene(GameField())

    def Update(self):
        pass

    def write(self, msg="pygame is cool"):
        myfont = pg.font.SysFont("./l/Pixeboy-z8XGD.ttf", 100)
        mytext = myfont.render(msg, True, (0, 0, 0))
        mytext = mytext.convert_alpha()
        return mytext

    def Render(self, screen):
        screen.blit(get_image('./l/loss.jpg'), (0, 0))
        textsurface1 = self.write('YOU LOST (but we love you no matter what)')
        screen.blit(textsurface1, (280, 400))


launch(1000, 800, 60, MainMenu())
