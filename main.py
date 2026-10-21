import time
import random

class StickmanRagdoll:
    def __init__(self):
        self.health = 100
        self.pupil_dilation = 50  # 0 = completely constricted, 100 = completely dilated
        self.digestion_rhythm = 0
        self.temperature = 98.6
        self.w_axis_position = 0
        print("A new Stickman Ragdoll has spawned!")

    def update(self):
        # Update biological and dimensional state
        self.process_vestibular()
        self.process_pupils()
        self.process_allergies()
        self.process_digestion()
        self.process_thermoregulation()
        self.process_4d_physics()

    def process_vestibular(self):
        """Inner-Ear Vestibular Mini-Game logic."""
        if random.random() < 0.05:
            print("WARNING: Whipped neck too fast! Camera flipped, uncontrollable breakdance initiated.")

    def process_pupils(self):
        """Manual Pupillary Dilation logic."""
        # Simulated transition to bright light
        if random.random() < 0.05 and self.pupil_dilation > 20:
            print("BLINDED! Stepped outside without constricting pupils. Stumbling into traffic.")

    def process_allergies(self):
        """The 'Allergy Sneeze Rocket' logic."""
        if random.random() < 0.05:
            print("ACHOO! Failed to filter pollen! Sneeze rocket launched backward at 60 MPH!")

    def process_digestion(self):
        """Digestive Peristalsis QTE logic."""
        if random.random() < 0.05:
            print("URGH... Missed digestion rhythm! Acid-reflux slapstick ragdoll spasms.")

    def process_thermoregulation(self):
        """Thermoregulation Shivers logic."""
        if self.temperature < 90:
            print("BRRR! Spamming alternate shoulder buttons to shiver. High-frequency vibrating mess!")

    def process_4d_physics(self):
        """The 4th Spatial Dimension (W-Axis Kicking) logic."""
        if random.random() < 0.05:
            print("MAX TORQUE KICK! Limb clipped into 4th dimension. Foot teleported out of a nearby trashcan.")

    def hospital_respawn(self):
        """Temporal Ragdoll Echo logic."""
        print("Waking up in hospital... left a 'temporal ghost' ragdoll at the crash site.")


def main():
    print("--- Welcome to the Biological Catastrophe Engine ---")
    player = StickmanRagdoll()

    # Simulate a brief game loop
    for tick in range(1, 10):
        print(f"\n--- Game Tick {tick} ---")
        player.update()
        time.sleep(0.5)  # Pause to make the simulation readable

    print("\nSimulation ended. Stickman probably in a vegetative state.")


if __name__ == "__main__":
    main()
