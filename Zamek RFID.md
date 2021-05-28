# Zamek RFID

Projekt opiera się na Raspberry Pi 4 i umożliwia otwieranie oraz zamykanie szafki za pomocą odpowiedniego identyfikatora w postaci karty lub breloczka RFID. 

Po przyłożeniu identyfikatora do czytnika RC-522 następuje odczytanie tokenów i przekazanie ich do RPI. W przypadku zgodności wprowadzonego w programie identyfikatora z numerem zbliżanej karty lub breloczka program wita się z właścicielem karty poprzez wyświetlenie na wyświetlaczu LCD np: `Welcome, Michal!`. Dodatkowo zapala się zielona dioda, która wraz z tekstem: `Access granted`, informuje o uzyskaniu dostępu. W tym momencie następuje ruch serva z pozycji 0 do pozycji 180 stopni powodując otwarcie zasuwki meblowej. 

W celu ponownego zamknięcia szafki należy ponownie przyłożyć odpowiedni token do czytnika, po czym nastąpi dwukrotne zapalanie i zgaszenie zielonej diody oraz wyświetlenie komunikatu: `Closing the lock`. Po zgaszeniu diod, serwo wraca do pozycji 0, a na wyświetlaczu pojawia się informacja o zamknięciu szafki: `Locked`.

Przyłożenie do czytnika karty z nieprawidłowym identyfikatora spowoduje zapalenie czerwonej diody oraz wyświetlenie informacji: `Invalid card`.

## Potrzebne elementy

1. Raspberry Pi 4
2. Wyświetlacz LCD 16x2
3. Czytnik RFID RC-522
4. Potencjometr 10k Ohm
5. Servo 9G
6. Dioda LED czerwona i zielona
7. Rezystor 330 Ohm x2

## Przygotowanie Raspberry PI

Do wykonania projektu będzie potrzebnych kilka bibliotek. W pierwszej kolejności należy wykonać aktualizacje RPI:

```bash
sudo apt-get update 
sudo apt-get upgrade
```

1. Instalacja Raspberry Pi GPIO Python Library - potrzebna do obsługi pinów GPIO oraz sterowania PWM:

```bash
sudo pip3 install RPi.GPIO
```

2. Instalacja RPLCD Library - potrzebna do wyświetlacza LCD i jego konfiguracji:

```bash
sudo pip3 install RPLCD
```

3. Instalacja MFRC422 Library - komunikacja z czytnikiem RFID:

Moduł czytnika RFID wykorzystuje interfejs SPI. W związku z tym należy się upewnić czy RPI ma aktywowany ten interfejs:

```bash
sudo raspi-config
```

Po wyświetleniu okna konfiguracyjnego z opcjami, należy przejść do "**5 Interfacing Options**", a następnie wybrać "**P4 SPI**" zatwierdzając enterem, oraz na pytanie o włączenie interfejsu SPI odpowiedzieć **Yes**.

Zanim SPI będzie całkowicie włączony należy zrestartować Raspberry:

```bash
sudo reboot
```

Jeśli po wpisaniu w konsolę `lsmod | grep spi` wyświetli się “**spi_bcm2835**” oznacza to że wszystko jest gotowe do dalszej pracy.

Do zainstalowania została jeszcze biblioteka odpowiedzialna za komunikacje z czytnikiem.

```bash
sudo pip3 install spidev
sudo pip3 install mfrc522
```



## Schemat połączenia

<img src="C:\Users\micha\Documents\GitHub\Raspberry Pi RFID Door Lock\DoorLock_bb.jpg" style="zoom:33%;" />

### Tabela połączeń

| RFID RC-522   | Raspberry Pi 4               |
| ------------- | ---------------------------- |
| Vcc (3,3V)    | 3,3V (fizyczny pin 1)        |
| RST           | GPIO 25                      |
| GND           | GND                          |
| RQ            | -                            |
| MISO          | GPIO 9                       |
| MOSI          | GPIO 10                      |
| SCK           | GPIO 11                      |
| SDA           | GPIO 8                       |
| **LCD 16x2**  |                              |
| Vss           | 5V (fizyczny pin 2)          |
| Vdd           | GND                          |
| V0            | środkowa nóżka potencjometru |
| RS            | GPIO 5                       |
| RW            | -                            |
| E             | GPIO 6                       |
| D0,D1,D2,D3   |                              |
| D4            | GPIO 13                      |
| D5            | GPIO 26                      |
| D6            | GPIO 16                      |
| D7            | GPIO 12                      |
| A,K           | -                            |
| **Servo 9G**  |                              |
| Vcc           | 5V                           |
| GND           | GND                          |
| Data          | GPIO 18 (PWM)                |
| **LED_GREEN** | GPIO 17                      |
| **LED_RED**   | GPIO 27                      |



## Sterowanie PWM

Położenie ramienia serwa zmienia się, podając odpowiedzi sygnał PWM. W zależności od parametrów sygnału, serwo może obracać w lewo/prawo, ustawić w jedną ze skrajnych pozycji (0 i 180 stopni), w pozycję neutralną (90 stopni) lub po prostu obrócić się o 360 stopni.  

Serwo oczekuje sygnału PWM o częstotliwości 50 Hz (cykl o długości 20 ms). Układ sterujący próbkuje długość stanu wysokiego. Może ona przyjmować charakterystyczne wartości które układ sterujący zinterpretuje jako: 

- 0,6 ms - ustaw serwo w pozycji skrajnej 0
- 1,5 ms - ustaw serwo w pozycji neutralnej (90 stopni)
- 2,5 ms - ustaw serwo w pozycji skrajnej 180 stopni

Podstawiając powyższe czasy do wzoru: $$wypełnienie = { t[ms] * 100] \over 20 [ms]}$$ , otrzymano odpowiednio wypełnienia: 3%, 7,5%, 12,5%.



## Kod programu

Aby korzystać z oznaczeń pinów jako GPIO, a nie ich fizycznej numeracji ustawiono tryb na BCM:

```python
GPIO.setmode(GPIO.BCM) 
```

W projekcie oprócz wyświetlacza LCD wykorzystano LEDy do informowania o poprawnym lub błędnym ID. Zieloną i czerwoną diodę podłączono odpowiednio do pinów GPIO 17 i GPIO 27. Dodatkowo sygnał z serwa podłączono pod GPIO 18 który jest pinem PWM.

```python
# --- definicja pinów wyjściowych ---
PWM_PIN = 18                                      
GREEN_LED = 17                                      
RED_LED = 27 

# --- definicja kanałów jako wyjścia ---
GPIO.setup(RED_LED,GPIO.OUT)
GPIO.setup(GREEN_LED,GPIO.OUT)
GPIO.setup(PWM_PIN, GPIO.OUT)  
```

Poniżej określono stałe wartości takie jak częstotliwość pracy PWM oraz prawidłowe ID karty, które umożliwi otworzenie drzwi.

```python
freq = 50                                           # częstotliowść przebiegu PWM
correctID = 387886317638                            # Prawidłowe ID
count = 0
```

`count` służy do zliczania liczby przyłożonej karty.

#### Wyświetlacz

Dzięki bibliotece RPLCD można bardzo łatwo skonfigurować podłączany wyświetlacz LCD.

```python
# Konfiguracja wyświetlacza LCD
lcd = CharLCD(numbering_mode=GPIO.BCM, pin_rs=5, pin_e=6, pins_data=[13, 26, 16, 12], cols=16, rows=2, dotsize=8, charmap='A02', auto_linebreaks=False)
```

`numbering_mode` określa konwencje oznaczeń pinów, a następnie do każdego pinu w wyświetlaczu przypisywane są odpowiednie numery pinów na płytce RPI. 

Wyświetlacz wykorzystany w projekcie ma 2 wiersze i możliwość zapisania 16 znaków w każdym z nich. Dlatego `cols` i `rows` przyjmują takie wartości. 

`charmap` odpowiada za wyświetlanie znaków. Domyślnie jest to wartość A02, jednak w przypadku niepoprawnego wyświetlania niektórych znaków należy zmienić na A00.

`auto_linebreaks` jest to automatyczny podział wierszy. Jeśli tekst nie będzie mieścił się w 16 znakach, to zostanie automatycznie przeniesiony do kolejnego wiersza.

#### Odczyt ID z karty

Odczyt danych z karty odbywa się za pomocą biblioteki mfrc522

```python
id = reader.read()
```

#### Przyłożono poprawną kartę 

W programie sprawdzany jest warunek czy ID zbliżonej karty jest równej prawidłowemu ID zdefiniowanemu na początku kodu.

Jeśli warunek zostanie spełniony następuje zwiększenie licznika zbliżeń karty o jeden 					`count = count + 1` , a następnie wykonanie poniższego kodu:

```python
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
  sleep(0.5)      
```

Prawidłowe ID powoduje przywitanie właściciela karty oraz poinformowanie o przyznanym dostępie. Dalej zostaje zapalona zielona dioda oraz ruch serwa do pozycji skrajnej 180 stopni, co powoduje otworzenie zamka.

W celu ponownego zamknięcia zamka, należy jeszcze raz przyłożyć kartę do czytnika po czym licznik zbliżeń osiągnie wartość równą dwa co spowoduje wykonanie poniższego kodu:

```python
lcd.clear()                             # Czyszczenie ekranu
lcd.write_string("Closing the")         # Wyświetlenie informacji o zamykaniu zamka 				w pierwszym wierszu
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
```

Użytkownik zostaje poinformowany o zamykaniu zamka i następuje dwu krotne odliczanie za pomocą zielonej diody która się zapali i zgaśnie po czym serwo zmieni swoja pozycję na 0 stopni. Te działanie zostanie zakończone informacją potwierdzającą zamknięcie zamka. 



#### Przyłożono niepoprawną kartę

```python
 lcd.clear()                                 # Czyszczenie ekranu
 lcd.write_string("Invalid card")            # Wyświetlenie informacji o błędnej karcie dostępu
 GPIO.output(RED_LED,GPIO.HIGH)              # Zapalenie GREEN_LED
 sleep(1)                                    # Czekanie 1s
 lcd.clear()                                 # Czyszczenie ekranu
 GPIO.output(RED_LED,GPIO.LOW)               # Zgaszenie GREEN_LED
```

Przyłożenie nieprawidłowej karty spowoduje poinformowanie o tym fakcie za pomocą czerwonej diody oraz wiadomości: `Invalid card`



## Dalszy rozwój projektu

Niestety servo nie posiada wystarczającej mocy aby otwierać/zamykać duże i mocne zamki. Więc aby to osiągnąć należałoby wykorzystać elektromagnes lub większy silnik połączony z przekaźnikiem. A jakakolwiek próba wejścia z nieprawidłowym ID może spowodować wysłanie informacji na mail lub telefon. 

W przypadku większej ilości osób które miałby dostęp do pomieszczenia/szafki należałoby stworzyć baze danych do przechowywania identyfikatorów i ich właścicieli. 

Dodatkowo projekt może zostać wykorzystany nie tylko do otwierania/zamykania zamka, ale również chociażby do odsłaniania rolet, czy włączania różnych urządzeń. 
