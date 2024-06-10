#!/usr/bin/env python3

def main():
    try:
        number1 = float(input("Enter the first floating number for 'water_threshold': "))
        number2 = float(input("Enter the second floating number for 'rain_threshold': "))
    except ValueError:
        print("Please enter valid floating-point numbers.")
        return

    # Nom du fichier de sortie
    filename = "./node-exporter/initial_value.prom"

    # Écrit les valeurs dans le fichier dans le format spécifié
    with open(filename, 'w') as file:
        file.write(f"water_threshold {number1}\n")
        file.write(f"rain_threshold {number2}\n")

    print(f"The values have been written to the '{filename}' file.")

if __name__ == "__main__":
    main()
