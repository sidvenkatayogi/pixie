sides = []
level = 2
for c in range(0, 6):
    sides.append(list(range((c * level) + 1, ((c+1) * level) + 1)))

print(sides)