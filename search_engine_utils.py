import numpy as np
import itertools

def get_minimal_position_variance(word_positions):

    practically_inf = 10**9

    if len(word_positions) <= 1:
        return practically_inf

    # Initialize variables to store the best selection and minimum variance
    min_variance = practically_inf

    # Generate all possible combinations of positions (one from each word)
    for combination in itertools.product(*word_positions):
        # Calculate the variance for this combination
        variance = np.var(combination)

        # Update the best selection if this combination has a lower variance
        if variance < min_variance:
            min_variance = variance

    return min_variance

def group_positions(positions, snippet_size=20, max_groups=5):
        if not positions:
            return []

        # Sort the positions to simplify the grouping process
        positions.sort()

        # Initialize the first group with the first position
        groups = [[positions[0]]]

        # Iterate through the sorted positions and group them
        for i in range(1, len(positions)):
            current_position = positions[i]
            last_group = groups[-1]
            first_position = last_group[0]

            # Check if the current position is within the window of length 20
            if current_position - first_position <= snippet_size:
                last_group.append(current_position)
            else:
                # If not, create a new group
                groups.append([current_position])

                if len(groups) >= max_groups:
                    break

        return list(map(lambda g: g[0], groups))

def build_string_from_dict(word_dict):
    # Initialize a list to store words at their positions
    word_positions = [''] * (max(max(positions) for positions in word_dict.values()) + 1)

    # Iterate through the dictionary and place words at their positions
    for word, positions in word_dict.items():
        for position in positions:
            word_positions[position] = word

    # Join the words to form the final string
    result_string = ' '.join(word_positions)

    return result_string