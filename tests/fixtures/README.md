# Fichiers audio de test

Générés par ffmpeg (sons sinusoïdaux synthétiques), jamais de vraie voix :

| Fichier | Contenu | Commande |
|---|---|---|
| `reve_court.wav` | 3 s, 220 Hz, mono 8 kHz | `ffmpeg -f lavfi -i "sine=frequency=220:duration=3" -ac 1 -ar 8000 reve_court.wav` |
| `reve_court.webm` | 2 s, opus (format Chrome / Firefox) | `ffmpeg -f lavfi -i "sine=frequency=330:duration=2" -c:a libopus -b:a 16k reve_court.webm` |
| `reve_court.m4a` | 2 s, AAC (format Safari) | `ffmpeg -f lavfi -i "sine=frequency=440:duration=2" -c:a aac -b:a 32k reve_court.m4a` |
| `corrompu.webm` | 2000 octets aléatoires | `head -c 2000 /dev/urandom` |
| `vide.wav` | 0 octet | — |

L'enregistrement trop long est généré à la volée dans les tests (pas de gros fichier commité).
