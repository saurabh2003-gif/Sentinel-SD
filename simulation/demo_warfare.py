import sys
import os
import time

# Add parent directory to path to import from Sentinel-SD
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.continuous_warfare import RedTeam, BlueTeam

def run_visual_demo():
    red = RedTeam()
    blue = BlueTeam()
    
    print("\n" + "="*60)
    print("      SENTINEL V3.2: MODERN WARFARE LIVE DEMO")
    print("="*60 + "\n")
    
    attacks_to_show = 20
    
    for i in range(1, attacks_to_show + 1):
        attack = red.generate_attack()
        
        # Artificial delay for visual effect
        time.sleep(0.3)
        
        print(f"[*] ROUND {i}: Red Team Attacking...")
        # Truncate long attacks for display
        display_attack = (attack[:75] + '...') if len(attack) > 75 else attack
        print(f"    PAYLOAD: \"{display_attack}\"")
        
        start = time.time()
        result = blue.defend(attack)
        duration = (time.time() - start) * 1000
        
        if result['verdict'] == "MALICIOUS":
            print(f"    \033[92m[DEFENDED]\033[0m SENTINEL BLOCKED DETECTED THREAT")
            print(f"    VECTOR: {result['detected_vector']}")
            print(f"    SPEED:  {duration:.2f}ms")
        else:
            print(f"    \033[91m[BYPASS]\033[0m ATTACK SUCCEEDED (Learning in progress...)")
            blue.learn(attack)
            
        print("-" * 60)

    print("\n[INFO] Demo Complete.")
    print("[INFO] Full 100,000 round training is continuing in background.")

if __name__ == "__main__":
    run_visual_demo()
