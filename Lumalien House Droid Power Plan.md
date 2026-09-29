# Lumalien House Droid Parts and Orders

**Decision (Sep 29):** Power the Jetson with a rechargeable USB-C PD power bank and one finished USB-C-to-barrel cable. The earlier five-item Walmart battery cart is retired. No battery harness assembly, soldering, separate battery charger, or multimeter is needed for this Jetson power connection. Recharge the bank before use.

## Jetson mobile power — two finished items

- [UGREEN 145W 25,000 mAh 3-Port Power Bank, model 90597A](https://us.ugreen.com/products/ugreen-145w-power-bank-for-laptop) — one. Its USB-C1 output explicitly supports **15 V / 3 A (45 W)**, and its battery holds 90 Wh nominally. Listed at $64.99 when checked; price may change.
- [Adafruit USB-C PD to 5.5 × 2.5 mm barrel cable, **15 V** version, product 5451](https://www.adafruit.com/product/5451) — one. It requests 15 V, has a center-positive plug, and is rated for up to 5 A; this bank supplies 3 A at 15 V. Select the **15 V** variant, not 9 V, 12 V, or 20 V. Listed at $7.95 when checked, before shipping.

**Connection:** Charge the bank, plug the cable's USB-C end into **USB-C1 on the UGREEN bank**, and plug its round end into the **Jetson Orin Nano developer kit's 5.5 × 2.5 mm DC power jack**. The Jetson's own USB-C socket is for data, not power. The cable and bank negotiate the 15 V output; no exposed battery wiring is involved. A USB-C PD wall charger is useful for recharging the bank quickly; the bank includes a short USB-C cable, but its product page does not say a wall charger is included. Check what charger is already on hand before adding one.

**Power limit:** This pair provides up to 45 W at 15 V, comparable in wattage to the kit's supplied 19 V / 2.37 A adapter. It is a practical first-build power source, not a measured guarantee for every possible USB load or highest sustained performance mode. Start with normal power settings and run the complete camera, LiDAR, microphone, and sound-card load on the bench; if the Jetson resets, use a higher-output battery solution before mobile use. The bank's 90 Wh is nominal; measure actual runtime with the assembled droid.

## Other purchases

- **Jetson Orin Nano Super Developer Kit:** [NVIDIA kit information](https://developer.nvidia.com/embedded/jetson-developer-kits). Pick the retailer and delivered price when ordering.
- **One complete Slamtec RPLIDAR C1 kit:** [Waveshare RPLIDAR C1 (SKU 26535)](https://www.waveshare.com/product/modules/sensors/rplidar-c1.htm) — one. The package-content image confirms the C1, adapter, and USB Type-A to Type-C cable; no separate LiDAR cable order. Add it to the same Waveshare cart as the USB TO AUDIO module if the delivered total makes sense.
- **One Waveshare USB TO AUDIO module:** [Waveshare specifications](https://www.waveshare.com/usb-to-audio.htm); [Amazon listing to check](https://www.amazon.com/dp/B08R38TXXL). Confirm the owned speaker plugs and impedance fit before ordering.

## Already owned — do not reorder

Two Acxico 3–6 V N20 motors, Adafruit Motor Bonnet, four-AA motor battery pack, USB Arducam camera, USB microphone, and Waveshare speakers.

## Build notes

- **Drive power:** Separate four-AA pack → Motor Bonnet → two N20 motors. The Bonnet uses Jetson 3.3 V logic and I2C; bench-test that connection and the motors under load. It does not power the Jetson.
- **USB:** C1, Arducam, USB microphone, and sound card occupy the Jetson's four USB-A ports. The existing speakers connect to the sound card only after their connector and electrical fit are confirmed.
- **Wheel encoders:** Do **not** order them for the first build. Start with the owned motors and test LiDAR scan-matching odometry. Add two matching encoded motors later if turns or room-to-room localization drift too much. The camera helps with visual recognition but is not automatically a wheel-odometry or depth sensor.
- **Safety:** A 2D LiDAR scans one plane, so test for objects outside that plane and add a bumper or close-range safeguard before unattended roaming.
