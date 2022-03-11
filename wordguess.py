import json
import math
import sys
import argparse
import random
import time

def max_entropy(reward_dict: dict):
    return max(reward_dict.values())

def expected_entropy(reward_dict: dict):
    # Assume that each pool in the reward_dict is a uniform distribution
    # Assume that the chance of landing in one of these pools is
    # the pool size over the total size
    total_events = sum(reward_dict.values())
    e_h = 0.0
    for r in reward_dict.values():
        e_h += r * math.log(r) / math.log(2.0)
    return e_h / total_events

def test_entropy():
    test_dist = {"a":4, "b":4, "c":4, "d":4}
    # Surprisingly, this assert works!  No problems with roundoff error?
    assert(expected_entropy(test_dist) == 2.0)

def write_reward(rs:str, guess_indices: list, word_indices: list):

    # Universe of available matches
    remaining = len(word_indices)

    # Run through all the guesses looking for exact matches
    for i in guess_indices:
        if i in word_indices:
            remaining -= 1
            rs =rs[0:i]+"m"+rs[i+1:]

    # Run through all the guesses again setting all possible wrong location
    # matches
    for i in guess_indices:
        if rs[i] == "m": continue
        if remaining > 0: rs=rs[0:i]+"w"+rs[i+1:]
        remaining -= 1
    return rs

def letter_locations_dict(word: str):
    ret_dict = {}
    for letter in word: 
        if letter not in ret_dict: 
            ret_dict[letter]= [i for i,l in enumerate(word) if l==letter]
    return ret_dict

def assemble_wordlists(guess:str, wordlist: list):

    # We will fill our reward string with
    # "-" for no match
    # "m" for a match in that location
    # "W" for a a match to the letter, but in the wrong location
    # The rules will be that exact matches take priority followed
    # by wrong location matches.  So for example if the word is 
    # "weeds" and the user guesses 
    # "emeer", the reward string would be 
    # "w-m--"

    split_dict = {}
    g_indices = letter_locations_dict(guess)
    for word in wordlist:
        reward_string = "-"*5
        w_indices = letter_locations_dict(word)
        for l in g_indices.keys() & w_indices.keys(): 
            reward_string = write_reward(reward_string, 
                        g_indices[l], w_indices[l])
        split_dict.setdefault(reward_string, []).append(word)
    len_dict = {key:len(split_dict[key]) for key in split_dict.keys()}
    sorted_len = dict(sorted(len_dict.items(), key=lambda x:x[1], reverse=True))
    ret_dict = {key:split_dict[key] for key in sorted_len.keys()}
    return ret_dict


def find_best_guesses(master_wordlist: list, wordlist: list, entropy_type =
        "expected Shannon"):

    # We will fill our reward string with
    # "-" for no match
    # "m" for a match in that location
    # "w" for a a match to the letter, but in the wrong location
    # The rules will be that exact matches take priority followed
    # by wrong location matches.  So for example if the word is 
    # "weeds" and the user guesses 
    # "emeer", the reward string would be 
    # "w-m--"

    entropy = expected_entropy
    if entropy_type == "max": 
        entropy = max_entropy
    E_H = {}
    best_guess = ""
    # Max entropy should be at the most log base 2 -- this is bigger
    best_entropy = 2 * len(wordlist)

    counter = 0
    step = int(0.5 + len(master_wordlist) / 100.0)
    steps = 0
    print_results = (len(wordlist) > 1000)
    for guess in master_wordlist:
        if print_results and counter % step == 0: 
            print("\r",steps,"%",file=sys.stderr,end="")
            steps += 1
        counter += 1
        reward_dict = {}
        g_indices = letter_locations_dict(guess)
        for word in wordlist:
            reward_string = "-"*5
            w_indices = letter_locations_dict(word)
            for l in g_indices.keys() & w_indices.keys(): 
                reward_string = write_reward(reward_string, 
                            g_indices[l], w_indices[l])
            if reward_string not in reward_dict:
                reward_dict[reward_string] = 1
            else:
                reward_dict[reward_string] += 1
        E_H[guess] = entropy(reward_dict)
        if E_H[guess] < best_entropy:
            best_guess = guess
            best_entropy = E_H[guess]
        elif E_H[guess] == best_entropy:
            if guess in wordlist: best_guess = guess
    if print_results:print("")
    sorted_E_H = dict(sorted(E_H.items(), key=lambda x:x[1], reverse=False))
    wordlists = assemble_wordlists(best_guess, wordlist)
    return wordlists, sorted_E_H, best_guess

def recursive_solver(
        master_wordlist: list, 
        wordlists: dict, 
        depth_limit: int, 
        current_depth: int,
        num_options: int,
        min_wordlist_len: int,
        results_dict: dict,
        entropy_type="expected Shannon"):

    at_max_depth = (current_depth+1 == depth_limit)
    if at_max_depth: 
        num_items = num_options
    else:
        num_items = 1
    for j in wordlists:
        if len(wordlists[j]) >= min_wordlist_len:
            if len(wordlists[j]) == 1:
                if j == "m"*len(j):
                    results_dict[j] = {"Solution guess "+str(current_depth):\
                        wordlists[j][0]}
                    continue
                results_dict[j] = {"Solution guess "+str(current_depth+1):\
                        wordlists[j][0]}
                continue
            next_wordlists, E_H, best_guess = \
                    find_best_guesses(master_wordlist,wordlists[j], entropy_type)
            if num_items == 1: 
                # We have to take best guess here, otherwise we might list 
                # a guess with equivalent entropy, but not in the solution set
                top_items=[best_guess]
            else:
                top_items = dict(list(E_H.items())[:num_items])
            results_dict[j]={"guess "+str(current_depth+1):best_guess}

            if not at_max_depth: 
                recursive_solver(
                        master_wordlist = master_wordlist,
                        wordlists = next_wordlists,
                        depth_limit = depth_limit,
                        current_depth = current_depth+1,
                        num_options = num_options,
                        min_wordlist_len = min_wordlist_len,
                        results_dict = results_dict[j],
                        entropy_type = entropy_type)

def retrieve_guess_result(wordlist_dict_keys: list): 
    guess_result = "" 
    starting_result_loop = True 
    while guess_result not in wordlist_dict_keys:
        if not starting_result_loop:
            print("Invalid result.  Valid results are:",
                    wordlist_dict_keys)
        guess_result = input(str(guess_count)+". Enter result: ")
        starting_result_loop = False
    return guess_result

def retrieve_guess(master_wordlist: dict, best_guess:str, guess_count:int):
    guess = "-"
    while guess not in master_wordlist:
        guess = input(str(guess_count)+". Enter word guess ("+best_guess+"): ")
        if guess == "": guess = best_guess
    return guess

if __name__ == "__main__":
    #test_entropy()
    parser = argparse.ArgumentParser()
    # -w doesn't actually do anything.  It is the default anyway
    parser.add_argument("-w", "--word_guess", action="store_true",
            help="Default behavior -- guess the word! Play a game against the computer")
    parser.add_argument("-e", "--exhaust", action="store_true",
            help="Create a tree of strategies.")
    parser.add_argument("-p", "--play", action="store_true", 
            help="Computer helps you play -- provides best guess at each stage.")
    parser.add_argument("wordlist_file", 
            help="name of a file containing a wordlist", type=str)
    parser.add_argument("-s", "--solutions_wordlist", 
            help="name of a file containing solutions wordlist", type=str)
    parser.add_argument("-d", "--depth", help="parameter for exhaustion: tree depth. Default=2", 
            type=int, default=2)
    parser.add_argument("-u", "--uselist", 
            help="Computer helps you play.  Use fixed first guess",
            action="store_true")
    parser.add_argument("-n", "--options", 
            help="parameter for exhaustion: number of options to offer at bottom level. Default=5", 
            default=5, type=int)
    parser.add_argument("-m", "--min_list_size", 
            help="parameter for exhaustion:  minimum size of list that will be evaluated. Default=100", 
        default=100, type=int)
    parser.add_argument("-f", "--file",
            help="parameter for exhaustion:  name of output json file")
    parser.add_argument("-l", "--word_length", 
            help="length of words to consider. Default=5",
            default=5, type=int)
    parser.add_argument("-a", "--entropy_type", help="type of entropy to use")
    args = parser.parse_args()


    with open(args.wordlist_file, "r") as infile:
        original_wordlist = infile.read().splitlines()

    solutions_wordlist = args.solutions_wordlist
    if solutions_wordlist is None:
        solutions_wordlist = args.wordlist_file
    master_wordlist = [x for x in original_wordlist if len(x) ==
        args.word_length]
    with open(solutions_wordlist, "r") as infile:
        possible_solutions = infile.read().splitlines()
    wordlists = {"start":possible_solutions}
    entropy_type="expected Shannon"
    if args.entropy_type is not None:
        entropy_type = args.entropy_type

    if args.play or args.uselist:
        guess_count = 1
        wordlist  = possible_solutions
        print_thresh = 21
        if args.uselist:
            with open("canned_first_option.json", "r") as infile:
                config_dict = json.load(infile)
            best_guess = config_dict["guess"]
            wordlist_dict = config_dict["wordlist_dict"]
            print(str(guess_count)+": "+best_guess)
            guess_result = retrieve_guess_result(list(wordlist_dict.keys()))
            wordlist = wordlist_dict[guess_result]
            print(str(len(wordlist))+" possibilities remaining.")
            if len(wordlist) < print_thresh:
                for i in wordlist: print(i)
            guess_count += 1

        wordlist_dict, E_H, best_guess = \
                find_best_guesses(master_wordlist, wordlist, entropy_type)
        guess_result = ""
        while guess_result != "m"*args.word_length:
            guess = retrieve_guess(master_wordlist, best_guess, guess_count)
            #guess = input(str(guess_count)+". Enter word guess ("+best_guess+"): ")
            #if guess == "": guess = best_guess
            wordlist_dict = assemble_wordlists(guess, wordlist)
            guess_result = retrieve_guess_result(list(wordlist_dict.keys()))
            if guess_result == "m"*args.word_length:
                print('Congratulations on finding "'+guess+'" in '\
                        +str(guess_count)+' tries!')
                break
            wordlist = wordlist_dict[guess_result]
            possibilities = len(wordlist_dict[guess_result])
            if possibilities == 1:
                print("One possibility remaining")
            else:
                print(possibilities, "possibilities remaining")
            if possibilities < print_thresh:
                for i in wordlist_dict[guess_result]: print(i)
            wordlist_dict, E_H, best_guess = find_best_guesses(master_wordlist,
                    wordlist_dict[guess_result], entropy_type)
            guess_count += 1
    elif args.exhaust:
        results_dict = {}
        recursive_solver(
            master_wordlist = master_wordlist,
            wordlists = wordlists,
            depth_limit = args.depth,
            current_depth = 0,
            num_options = args.options,
            min_wordlist_len = args.min_list_size,
            results_dict = results_dict,
            entropy_type = entropy_type)
        if args.file is not None:
            with open(args.file, "w") as outfile:
                json.dump(results_dict["start"], outfile, indent=2)
    else: #do wordguess
        random.seed(time.time())
        secret_word = random.choice(possible_solutions)
        secret_indices = letter_locations_dict(secret_word)
        guess = ""
        result = ""
        guess_count = 1
        while guess != secret_word:
            guess = input(str(guess_count)+". ")
            if guess not in master_wordlist:
                continue
            g_indices = letter_locations_dict(guess)
            reward_string = "-"*args.word_length
            for l in g_indices.keys() & secret_indices.keys(): 
                reward_string = write_reward(reward_string, 
                        g_indices[l], secret_indices[l])
            print("   "+reward_string)
            guess_count += 1
        print("The secret word was",secret_word)
