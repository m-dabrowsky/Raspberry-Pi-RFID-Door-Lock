import RPi.GPIO as GPIO                             # Obsługa pinów GPIO i PWM
from time import sleep                              # Biblioteka do wykorzystania funkcji sleep()
from mfrc522 import SimpleMFRC522                   # Biblioteka obsługi czytnika RFID
from RPLCD.gpio import CharLCD                      # Obsługa wyświetlacza LCD

GPIO.setwarnings(False)                             # wyłączenie ostrzeżeń podczas pracy kodu
"""-----------------------------------------"""
GPIO.setmode(GPIO.BCM)                              # konfiguracja konwencji oznaczenia pinów GPIO

# --- definicja pinów wyjściowych ---
PWM_PIN = 18                                        # Sygnał PWM ma być wygenerowany na GPIO18, czyli fizyczny pin 12
GREEN_LED = 17                                      # Dioda zielona informująca o poprawnym ID
RED_LED = 27                                        # Dioda czerwona informująca o błędnym ID

# --- definicja kanałów jako wyjścia ---
GPIO.setup(RED_LED,GPIO.OUT)
GPIO.setup(GREEN_LED,GPIO.OUT)
GPIO.setup(PWM_PIN, GPIO.OUT)  

freq = 50                                           # częstotliowść przebiegu PWM
correctID = 387886317638                            # Prawidłowe ID
count = 0

"""-----------------------------------------"""

reader = SimpleMFRC522()                            # Stworzenie instancji

# Konfiguracja wyświetlacza LCD
lcd = CharLCD(numbering_mode=GPIO.BCM, pin_rs=5, pin_e=6, pins_data=[13, 26, 16, 12],
              cols=16, rows=2, dotsize=8,
              charmap='A02',
              auto_linebreaks=False)


pwm = GPIO.PWM(PWM_PIN,freq)                        # definicja kanału PWM na pinie (18) i częstotliwości 50 Hz (20ms)

# Uruchomienie PWM: 3 oznacza wypełnienie 3% czyli pozycja 0
pwm.start(3)
GPIO.output(PWM_PIN, True)


while True:
    lcd.clear()                                     # Czyszczenie ekranu
    lcd.write_string('Put your ID card')            # Wyświetlenie informacji o zbliżeniu karty

    id = reader.read()                              # Odczyt ID z karty
        
    if(id == correctID):                            # jeśli przyłozona karta jest zgodna z ID

        count = count + 1                           # Zwiększenie licznika (po ponownym przyłożeniu karty)
        if(count == 2):                             # Jeśli drugi raz przyłoży się kartę następuje zamknięcie zamka
            lcd.clear()                             # Czyszczenie ekranu
            lcd.write_string("Closing the")         # Wyświetlenie informacji o zamykaniu zamka w pierwszym wierszu
            lcd.cursor_pos = (1, 0)                 # Przejście do drugiego wiersza
            lcd.write_string('lock')
            for i in range(2):                      # Pętla odpowiedzialna za 2-krotne zapalenie i zgaszenie GREEN_LED
                GPIO.output(GREEN_LED, GPIO.LOW)
                sleep(1)
                GPIO.output(GREEN_LED, GPIO.HIGH)
                sleep(1)
                GPIO.output(GREEN_LED, GPIO.LOW)
            pwm.ChangeDutyCycle(3)                  # zmiana wypełnienia sygnału PWM (0 stopni)
            lcd.write_string("Locked")              # Wyświetlenie informacji o zamyknięciu zamka
            lcd.clear()                             # Czyszczenie ekranu
            count = 0                               # Wyzerowanie licznika
            sleep(0.5)                              # Czekanie 0.5s
        else:
            lcd.clear()                             # Czyszczenie ekranu
            lcd.write_string('Hello Michal!')       # Wyświetlenie przywitania
            sleep(1)                                # Czekanie 1s
            lcd.clear()                             # Czyszczenie ekranu
            lcd.write_string("Access granted")      # Wyświetlenie informacji o przyznanym dostępie
            GPIO.output(GREEN_LED, GPIO.HIGH)       # Zapalenie GREEN_LED

            pwm.ChangeDutyCycle(12.5)               # Zmiana wypełnienia sygnału PWM (180 stopni)
            sleep(1)                                # Czekanie 1s
            lcd.clear()                             # Czyszczenie ekranu
            GPIO.output(GREEN_LED, GPIO.LOW)        # Zgaszenie GREEN_LED
            sleep(0.5)                              # Czekanie 0.5s


        #GPIO.output(PWM_PIN, False)

    else:

        lcd.clear()                                 # Czyszczenie ekranu
        lcd.write_string("Invalid card")            # Wyświetlenie informacji o błędnej karcie dostępu
        GPIO.output(RED_LED,GPIO.HIGH)              # Zapalenie GREEN_LED
        sleep(1)                                    # Czekanie 1s
        lcd.clear()                                 # Czyszczenie ekranu
        GPIO.output(RED_LED,GPIO.LOW)               # Zgaszenie GREEN_LED
pwm.stop()
GPIO.cleanup()                                      # wyłączenie wszystkich kanałów PWM
