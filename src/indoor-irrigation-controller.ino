#include <Arduino.h>

// The temperature sensor is a 1-wire automotive thermistor that is wired as
// part of a voltage divider so that the ADC can be used to read a voltage
//NOTE: A6 & A7 are analog only pins, so A7 is used for the ADC input
#define TEMP_ADC_PIN                A7

// This controls an AC relay for running the recirculation pump
// NOTE: due to the attached LED D13 is really only useful as an output
#define PUMP_OUTPUT_PIN             13

// Each "mixing" valve is a motor + driver that is controlled with two pins. These valves
// also include two normally-open limit switches. Driving the valve should be done with 0.5second pulses
//   0,0 = stationary
//   0,1 = open
//   1,0 = close
//   1,1 = Not used
#define COLD_MIX_OUT_A              12
#define COLD_MIX_OUT_B              11
#define COLD_MIX_CLOSED_INPUT       10
#define COLD_MIX_OPENED_INPUT       9

#define HOT_MIX_OUT_A               8
#define HOT_MIX_OUT_B               7
#define HOT_MIX_CLOSED_INPUT        6
#define HOT_MIX_OPENED_INPUT        5

// Each open/close valve uses a NC/NO/COM relay and a single wire toggle (open/close) for control
// Feedback from the two limit switches is tied together. 1 = MOVINNG, 0=STOPPED
#define RECYCLE_VALVE_CONTROL       4
#define RECYCLE_VALVE_INPUT         3
#define OUTPUT_VALVE_CONTROL        2
#define OUTPUT_VALVE_INPUT          A0


// Constants
#define SEC_TO_MS                   1000
#define ANALOG_READS                64
#define VALVE_INCREMENTS            10
// The docs on these valves say 6 to 8 seconds for full movement
// But when pulsing, the momentum carries the valve a little further
#define VALVE_PULSE_DELAY           4*1000/VALVE_INCREMENTS


//  Globals
float TEMPERATURE = 0.0;
uint8_t COLD_POSITION = 0;
uint8_t HOT_POSITION = 0;
char OUTPUT_POSITION = 'o';
char RECIRCULATION_POSITION = 'r';


void debug(String msg)
{
    Serial.print("D - ");
    Serial.println(msg);
}


float mapf(float x, float in_min, float in_max, float out_min, float out_max)
{
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

float convertToFahrenheit(float value) {
    // FIXME: Implement conversion function or lookup table
    // 130F = 48
    // 44F = 280

    // If linear 87F == 164
    return mapf(value, 280.0, 48.0, 44.0, 130.0);
}

void readTemperature() {
    uint32_t sum = 0;
    float value = 0;
    for (uint8_t x=0; x< ANALOG_READS; x++) {
        sum = sum + analogRead(TEMP_ADC_PIN);
    }

    value = sum / ANALOG_READS;
    TEMPERATURE = convertToFahrenheit(value);
}


void pulseColdOpen() {
    if (COLD_POSITION == VALVE_INCREMENTS) {
        return;
    }
    COLD_POSITION++;

    do {
        digitalWrite(COLD_MIX_OUT_A, HIGH);
        digitalWrite(COLD_MIX_OUT_B, LOW);

        delay(VALVE_PULSE_DELAY);

        digitalWrite(COLD_MIX_OUT_A, LOW);
        digitalWrite(COLD_MIX_OUT_B, LOW);
    }
    while(digitalRead(COLD_MIX_OPENED_INPUT) == HIGH && COLD_POSITION == VALVE_INCREMENTS);
}

void pulseColdClosed() {
    if (COLD_POSITION == 0) {
        return;
    }

    COLD_POSITION--;

    do { 
        digitalWrite(COLD_MIX_OUT_A, LOW);
        digitalWrite(COLD_MIX_OUT_B, HIGH);

        delay(VALVE_PULSE_DELAY);

        digitalWrite(COLD_MIX_OUT_A, LOW);
        digitalWrite(COLD_MIX_OUT_B, LOW);

    }
    while(digitalRead(COLD_MIX_CLOSED_INPUT) == HIGH && COLD_POSITION == 0);
}

void pulseHotOpen() {
    if (HOT_POSITION == VALVE_INCREMENTS) {
        return;
    }

    HOT_POSITION++;

    do {
        digitalWrite(HOT_MIX_OUT_A, HIGH);
        digitalWrite(HOT_MIX_OUT_B, LOW);

        delay(VALVE_PULSE_DELAY);

        digitalWrite(HOT_MIX_OUT_A, LOW);
        digitalWrite(HOT_MIX_OUT_B, LOW);
    }
    while(digitalRead(HOT_MIX_OPENED_INPUT) == HIGH && HOT_POSITION == VALVE_INCREMENTS);
}

void pulseHotClosed() {
    if (HOT_POSITION == 0) {
        return;
    }

    HOT_POSITION--;

    do {
        digitalWrite(HOT_MIX_OUT_A, LOW);
        digitalWrite(HOT_MIX_OUT_B, HIGH);

        delay(VALVE_PULSE_DELAY);

        digitalWrite(HOT_MIX_OUT_A, LOW);
        digitalWrite(HOT_MIX_OUT_B, LOW);
    }
    while(digitalRead(HOT_MIX_CLOSED_INPUT) == HIGH && HOT_POSITION == 0);
}

void openOutput() {
    digitalWrite(OUTPUT_VALVE_CONTROL, HIGH);
    OUTPUT_POSITION = 'O';
}

void closeOutput() {
    digitalWrite(OUTPUT_VALVE_CONTROL, LOW);
    OUTPUT_POSITION = 'o';
}

void startPump() {
    digitalWrite(PUMP_OUTPUT_PIN, HIGH);
}

void stopPump() {
    digitalWrite(PUMP_OUTPUT_PIN, LOW);
}

void openRecirculation() {
    digitalWrite(RECYCLE_VALVE_CONTROL, HIGH);
    RECIRCULATION_POSITION = 'R';
}

void closeRecirculation() {
    digitalWrite(RECYCLE_VALVE_CONTROL, LOW);
    RECIRCULATION_POSITION = 'r';
}

void updateValvePositions() {
    // COLD Water Valve
    if (digitalRead(COLD_MIX_CLOSED_INPUT) == LOW) {
        COLD_POSITION = 0;
    } else if (digitalRead(COLD_MIX_OPENED_INPUT) == LOW) {
        COLD_POSITION = VALVE_INCREMENTS;
    }

    // HOT Water Valve
    if (digitalRead(HOT_MIX_CLOSED_INPUT) == LOW) {
        HOT_POSITION = 0;
    } else if (digitalRead(HOT_MIX_OPENED_INPUT) == LOW) {
        HOT_POSITION = VALVE_INCREMENTS;
    }
}

void printValves()
{
    for (uint8_t x=0; x<COLD_POSITION; x++) {
        Serial.print('C');
    }
    for (uint8_t x = 0; x < HOT_POSITION; x++)
    {
        Serial.print('H');
    }

    // FIXME: add valve status (when in transition)
    Serial.print(OUTPUT_POSITION);
    Serial.print(RECIRCULATION_POSITION);

    Serial.println();
}


void setup() {
    // Setup the serial connection
    Serial.begin(57600);

    // Setup ADC pin for temp; A6 &A7 don't need any setup

    // Setup pump output (default to off)
    pinMode(PUMP_OUTPUT_PIN, OUTPUT);
    stopPump();

    // Setup cold water valve (defalut to no movement)
    pinMode(COLD_MIX_OUT_A, OUTPUT);
    pinMode(COLD_MIX_OUT_B, OUTPUT);
    digitalWrite(COLD_MIX_OUT_A, LOW);
    digitalWrite(COLD_MIX_OUT_B, LOW);
    pinMode(COLD_MIX_CLOSED_INPUT, INPUT_PULLUP);
    pinMode(COLD_MIX_OPENED_INPUT, INPUT_PULLUP);

    // Setup hot water valve (default to no movement)
    pinMode(HOT_MIX_OUT_A, OUTPUT);
    pinMode(HOT_MIX_OUT_B, OUTPUT);
    digitalWrite(HOT_MIX_OUT_A, LOW);
    digitalWrite(HOT_MIX_OUT_B, LOW);
    pinMode(HOT_MIX_CLOSED_INPUT, INPUT_PULLUP);
    pinMode(HOT_MIX_OPENED_INPUT, INPUT_PULLUP);

    // Setup water recycle valve (default to closed)
    pinMode(RECYCLE_VALVE_CONTROL, OUTPUT);
    pinMode(RECYCLE_VALVE_INPUT, INPUT_PULLUP);
    closeRecirculation();

    //  Setup the Output water valve (default is closed)
    pinMode(OUTPUT_VALVE_CONTROL, OUTPUT);
    pinMode(OUTPUT_VALVE_INPUT, INPUT_PULLUP);
    closeOutput();

    // Initialize Variables
    readTemperature();

    debug("STARTUP Complete");
}

void loop() {
    if (Serial.available() > 0) {
        char code = Serial.read();
        switch(code) {
            case 'C':
                // Pulse the cold valve a little more open
                Serial.println('C');
                pulseColdOpen();
                break;

            case 'c':
                // Pulse the cold valve a little more closed
                Serial.println('c');
                pulseColdClosed();
                break;

            case 'H':
                // Pulse the hot valve a little more open
                Serial.println('H');
                pulseHotOpen();
                break;

            case 'h':
                // Pulse the hot valve a little more closed
                Serial.println('h');
                pulseHotClosed();
                break;

            case 'I':
                Serial.println('I');
                break;

            case 'O':
                // Open the output valve
                Serial.println('O');
                openOutput();
                break;

            case 'o':
                // Close the output valve
                Serial.println('o');
                closeOutput();
                break;

            case 'P':
                // Turn on the pump
                Serial.println('P');
                startPump();
                break;

            case 'p':
                // Turn off the pump
                Serial.println('p');
                stopPump();
                break;

            case 'R':
                // Open the recirculation valve
                Serial.println('R');
                openRecirculation();
                break;

            case 'r':
                // Close the recirculation valve
                Serial.println('r');
                closeRecirculation();
                break;

            case 'T':
                readTemperature();
                Serial.println(TEMPERATURE);
                break;

            case 'V':
                printValves();
                break;

            default:
                Serial.println('E');
                break;
        }
    }

    updateValvePositions();
}
