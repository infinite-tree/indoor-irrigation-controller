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

// Each open/close valve has a 2 wire control also driven through a driver and contains outputs for limit switches.
// The valves however will automitcall stop when limits are hit and can be treated as having two simple states:
//   0,1 = closed
//   1,0 = open
// NOTE: if necessary, these can become one wire with an inverting schmitt trigger
#define RECYCLE_VALVE_CONTROL_A     4
#define RECYCLE_VALVE_CONTROL_B     3
#define OUTPUT_VALVE_CONTROL_A      2
#define OUTPUT_VALVE_CONTROL_B      A0


// Constants
#define ANALOG_READS                64
#define VALVE_INCREMENTS            10
// FIXME: how many seconds for full movement?
#define VALVE_PULSE_DELAY           2*1000/VALVE_INCREMENTS


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


float convertToFahrenheit(float value) {
    // FIXME: Implement conversion function or lookup table
    return value;
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
    // FIXME: verify direction
    COLD_POSITION++;
    digitalWrite(COLD_MIX_OUT_A, HIGH);
    digitalWrite(COLD_MIX_OUT_B, LOW);

    delay(VALVE_PULSE_DELAY);

    digitalWrite(COLD_MIX_OUT_A, LOW);
    digitalWrite(COLD_MIX_OUT_B, LOW);
}

void pulseColdClosed() {
    // FIXME: verify direction
    COLD_POSITION--;
    digitalWrite(COLD_MIX_OUT_A, LOW);
    digitalWrite(COLD_MIX_OUT_B, HIGH);

    delay(VALVE_PULSE_DELAY);

    digitalWrite(COLD_MIX_OUT_A, LOW);
    digitalWrite(COLD_MIX_OUT_B, LOW);
}

void pulseHotOpen() {
    // FIXME: verify direction
    HOT_POSITION++;
    digitalWrite(HOT_MIX_OUT_A, HIGH);
    digitalWrite(HOT_MIX_OUT_B, LOW);

    delay(VALVE_PULSE_DELAY);

    digitalWrite(HOT_MIX_OUT_A, LOW);
    digitalWrite(HOT_MIX_OUT_B, LOW);
}

void pulseHotClosed() {
    // FIXME: verify direction
    HOT_POSITION--;
    digitalWrite(HOT_MIX_OUT_A, LOW);
    digitalWrite(HOT_MIX_OUT_B, HIGH);

    delay(VALVE_PULSE_DELAY);

    digitalWrite(HOT_MIX_OUT_A, LOW);
    digitalWrite(HOT_MIX_OUT_B, LOW);
}

void openOutput() {
    // FIXME: verify direction
    digitalWrite(OUTPUT_VALVE_CONTROL_A, HIGH);
    digitalWrite(OUTPUT_VALVE_CONTROL_B, LOW);
    OUTPUT_POSITION = 'O';
}

void closeOutput() {
    // FIXME: verify direction
    digitalWrite(OUTPUT_VALVE_CONTROL_A, LOW);
    digitalWrite(OUTPUT_VALVE_CONTROL_B, HIGH);
    OUTPUT_POSITION = 'o';
}

void startPump() {
    digitalWrite(PUMP_OUTPUT_PIN, HIGH);
}

void stopPump() {
    digitalWrite(PUMP_OUTPUT_PIN, LOW);
}

void openRecirculation() {
    // FIXME: verify direction
    digitalWrite(RECYCLE_VALVE_CONTROL_A, HIGH);
    digitalWrite(RECYCLE_VALVE_CONTROL_B, LOW);
    RECIRCULATION_POSITION = 'R';
}

void closeRecirculation() {
    // FIXME: verify direction
    digitalWrite(RECYCLE_VALVE_CONTROL_A, LOW);
    digitalWrite(RECYCLE_VALVE_CONTROL_B, HIGH);
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
    pinMode(RECYCLE_VALVE_CONTROL_A, OUTPUT);
    pinMode(RECYCLE_VALVE_CONTROL_B, OUTPUT);
    closeRecirculation();

    //  Setup the Output water valve (default is closed)
    pinMode(OUTPUT_VALVE_CONTROL_A, OUTPUT);
    pinMode(OUTPUT_VALVE_CONTROL_B, OUTPUT);
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