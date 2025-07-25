#include <Arduino.h>
#include <DHT.h>

// Define the pin and sensor type
#define DHTPIN 2       // Digital pin connected to the DHT sensor
#define DHTTYPE DHT11  // Change to DHT22 if you're using that sensor

// Initialize DHT sensor
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
}

void loop() {
  // Drastically reduce delay to send data very frequently
  delay(50); // Changed from 1000ms to 50ms (0.05 seconds)

  // Read temperature and humidity
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // Celsius by default

  // Check if any reads failed
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // Print values to Serial Monitor
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print("°C  |  Humidity: ");
  Serial.print(humidity);
  Serial.println("%");
}
