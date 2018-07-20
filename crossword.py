import random, time
from operator import itemgetter
from collections import defaultdict
from ben.panlex_db import query
import panlex
import regex as re
import unicodedata2 as unicodedata
import puz
import json
# from grapheme_clusters import Gstr
from grapheme import graphemes

TRANS_QUERY = """
select 
    expr.txt, 
    denotationsrc.expr as trans_expr, 
    exprsrc.txt as trans_txt, 
    grp_quality_score(array_agg(denotation.grp), array_agg(denotation.quality)) as trans_quality 
    from expr 
    inner join denotationx as denotation on denotation.expr = expr.id 
    inner join 
        denotationx as denotationsrc on denotationsrc.meaning = denotation.meaning and 
        denotationsrc.expr != denotation.expr inner join expr as exprsrc on exprsrc.id = denotationsrc.expr 
        where expr.langvar = uid_langvar(%s) and 
        denotationsrc.expr in (select expr.id from expr where expr.langvar = uid_langvar(%s) and 
        expr.txt = any(%s)) 
        group by expr.id, denotationsrc.expr, exprsrc.txt 
        order by trans_quality desc
"""

puz.ENCODING = "UTF-8"
class Crossword(object):
    def __init__(self, rows, cols, empty=' ', available_words=[]):
        self.rows = rows
        self.cols = cols
        self.empty = empty
        self.available_words = available_words
        self.let_coords = defaultdict(list)

    def prep_grid_words(self):
        self.current_wordlist = []
        self.let_coords.clear()
        self.grid = [[self.empty]*self.cols for i in range(self.rows)]
        self.available_words = [word[:2] for word in self.available_words]
        self.first_word(self.available_words[0])

    def compute_crossword(self, time_permitted=1.00):
        self.best_wordlist = []
        wordlist_length = len(self.available_words)
        time_permitted = float(time_permitted)
        start_full = float(time.time())
        while (float(time.time()) - start_full) < time_permitted:
            self.prep_grid_words()
            [self.add_words(word) for i in range(2) for word in self.available_words
             if word not in self.current_wordlist]
            if len(self.current_wordlist) > len(self.best_wordlist):
                self.best_wordlist = list(self.current_wordlist)
                self.best_grid = list(self.grid)
            if len(self.best_wordlist) == wordlist_length:
                break
        #answer = '\n'.join([''.join(['{} '.format(c) for c in self.best_grid[r]]) for r in range(self.rows)])
        answer = '\n'.join([''.join([u'{} '.format(c) for c in self.best_grid[r]])
                            for r in range(self.rows)])
        return answer + '\n\n' + str(len(self.best_wordlist)) + ' out of ' + str(wordlist_length)

    def get_coords(self, word):
        """Return possible coordinates for each letter."""
        word_length = len(word[0])
        coordlist = []
        temp_list =  [(l, v) for l, letter in enumerate(word[0])
                      for k, v in self.let_coords.items() if k == letter]
        for coord in temp_list:
            letc = coord[0]
            for item in coord[1]:
                (rowc, colc, vertc) = item
                if vertc:
                    if colc - letc >= 0 and (colc - letc) + word_length <= self.cols:
                        row, col = (rowc, colc - letc)
                        score = self.check_score_horiz(word, row, col, word_length)
                        if score:
                            coordlist.append([rowc, colc - letc, 0, score])
                else:
                    if rowc - letc >= 0 and (rowc - letc) + word_length <= self.rows:
                        row, col = (rowc - letc, colc)
                        score = self.check_score_vert(word, row, col, word_length)
                        if score:
                            coordlist.append([rowc - letc, colc, 1, score])
        if coordlist:
            return max(coordlist, key=itemgetter(3))
        else:
            return

    def first_word(self, word):
        """Place the first word at a random position in the grid."""
        vertical = random.randrange(0, 2)
        if vertical:
            row = random.randrange(0, self.rows - len(word[0]))
            col = random.randrange(0, self.cols)
        else:
            row = random.randrange(0, self.rows)
            col = random.randrange(0, self.cols - len(word[0]))
        self.set_word(word, row, col, vertical)

    def add_words(self, word):
        """Add the rest of the words to the grid."""
        coordlist = self.get_coords(word)
        if not coordlist:
            return
        row, col, vertical = coordlist[0], coordlist[1], coordlist[2]
        self.set_word(word, row, col, vertical)

    def check_score_horiz(self, word, row, col, word_length, score=1):
        cell_occupied = self.cell_occupied
        if col and cell_occupied(row, col-1) or col + word_length != self.cols and cell_occupied(row, col + word_length):
            return 0
        for letter in word[0]:
            active_cell = self.grid[row][col]
            if active_cell == self.empty:
                if row + 1 != self.rows and cell_occupied(row+1, col) or row and cell_occupied(row-1, col):
                    return 0
            elif active_cell == letter:
                score += 1
            else:
                return 0
            col += 1
        return score

    def check_score_vert(self, word, row, col, word_length, score=1):
        cell_occupied = self.cell_occupied
        if row and cell_occupied(row-1, col) or row + word_length != self.rows and cell_occupied(row + word_length, col):
            return 0
        for letter in word[0]:
            active_cell = self.grid[row][col]
            if active_cell == self.empty:
                if col + 1 != self.cols and cell_occupied(row, col+1) or col and cell_occupied(row, col-1):
                    return 0
            elif active_cell == letter:
                score += 1
            else:
                return 0
            row += 1
        return score

    def set_word(self, word, row, col, vertical):
        """Put words on the grid and add them to the word list."""
        word.extend([row, col, vertical])
        self.current_wordlist.append(word)

        horizontal = not vertical
        for letter in word[0]:
            self.grid[row][col] = letter
            if (row, col, horizontal) not in self.let_coords[letter]:
                self.let_coords[letter].append((row, col, vertical))
            else:
                self.let_coords[letter].remove((row, col, horizontal))
            if vertical:
                row += 1
            else:
                col += 1

    def cell_occupied(self, row, col):
        cell = self.grid[row][col]
        if cell == self.empty:
            return False
        else:
            return True

# def epo_encoding_kludge(string):
#     s = unicodedata.normalize("NFKD", string)
#     return re.sub(r"\p{M}", "x", s)

def get_exprs(uid, limit=1000):
    r = query("""
        SELECT txt FROM exprx 
        WHERE langvar = uid_langvar(%s) 
        ORDER BY score DESC 
        LIMIT %s
        """, (uid, limit))
    return [ex.txt for ex in r if len(ex.txt) > 1]

def prep_string(string):
    return list(graphemes(re.sub(r"\s", "", string.upper())))

def prep_string_Arab(string):
    g = list(graphemes(re.sub(r"\s", "", string)))
    return [g[0] + "\u200d"] + ["\u200d" + c + "\u200d" for c in g[1:-1]] + ["\u200d" + g[1]]

def get_expr_trans(trans_uid, uid, limit=1000, sample=100, numtrans=3):
    ex_list = get_exprs(trans_uid, limit)
    ex_de = random.sample(ex_list, sample)
    tr = query(TRANS_QUERY, (trans_uid, uid, ex_de))
    tr_dict = defaultdict(list)
    for r in tr:
        tr_dict[r.trans_txt].append(r.txt)
    wl = [[prep_string(ex), " - ".join(tr_dict[ex][:numtrans])] for ex in ex_de]
    return wl

def gen_puzzle(puz_uid, hint_uid, size=(30, 30), limit=1000, sample=100, numtrans=3):
    wl = get_expr_trans(puz_uid, hint_uid, limit, sample, numtrans)
    c = Crossword(size[0], size[1], " ", wl)
    c.compute_crossword()
    return c

def gen_puzzle2(puz_uid, size=(30, 30), limit=1000, script="Zyyy"):
    exprs = get_exprs(puz_uid, limit)
    # if script == "Arab":
    #     wl = [[prep_string_Arab(expr), expr] for expr in exprs]
    # else:
    wl = [[prep_string(expr), expr] for expr in exprs]
    c = Crossword(size[0], size[1], "", wl)
    c.compute_crossword()
    return c

def translate_clues(crossword, puz_uid, clue_uid, numtrans=3):
    wl = crossword.best_wordlist
    ex_de = [clue[1] for clue in wl]
    # tr = panlex.query_all("/expr", {
    #     "trans_uid": puz_uid, 
    #     "uid": clue_uid, 
    #     "include": ["trans_quality", "trans_txt"], 
    #     "sort": "trans_quality desc", 
    #     "trans_txt": ex_de
    # })
    tr = query(TRANS_QUERY, (clue_uid, puz_uid, ex_de))
    tr_dict = defaultdict(list)
    for r in tr:
        tr_dict[r.trans_txt].append(r.txt)
    for clue in wl:
        clue[1] = " - ".join(tr_dict[clue[1]][:numtrans])
    crossword.best_wordlist = wl
    return crossword

def get_script(uid):
    query_string = """
        SELECT txt FROM expr WHERE expr.id = 
            (SELECT langvar.script_expr
             FROM langvar
             WHERE langvar.id = uid_langvar(%s))
    """
    return query(query_string, (uid,))[0].txt

             

def grid_to_solution(grid):
    return "".join(["".join(r).replace(" ", ".") for r in grid])

def crossword_to_puz(crossword):
    p = puz.Puzzle()
    p.preamble = b""
    p.title = "PanLex Crossword"
    p.author = "PanLex"
    p.copyright = "n/a"
    p.width = crossword.cols
    p.height = crossword.rows
    p.solution = grid_to_solution(crossword.best_grid)
    p.fill = re.sub(r"[^.]", "-", p.solution)
    p.clues = [w[1] for w in sorted(crossword.best_wordlist, key=lambda x: x[2:])]
    return p

def make_puz(puz_uid, hint_uid, size=(30, 30), limit=1000, sample=100, numtrans=3):
    c = gen_puzzle(puz_uid, hint_uid, size, limit, sample, numtrans)
    p = crossword_to_puz(c)
    p.save("PanLex_{}_{}.puz".format(puz_uid, hint_uid))

def make_json(puz_uid, hint_uid, size=(30, 30), limit=1000, sample=100, numtrans=3):
    script = get_script(puz_uid)
    if script == "Arab":
        rtl = True
    else:
        rtl = False
    c = translate_clues(gen_puzzle2(puz_uid, size, limit, script), puz_uid, hint_uid, numtrans)
    grid = []
    for row in c.best_grid:
        new_row = [cell if cell != " " else "" for cell in row]
        if rtl: new_row = new_row[::-1]
        grid.append(new_row)
    wl = []
    for clue in sorted(c.best_wordlist, key=lambda x: (x[4], x[2], x[3])):
        new_clue = clue[:]
        if rtl:
            new_clue[3] = len(grid[0]) - 1 - clue[3]
        wl.append(new_clue)
    allcaps = "".join(["".join(clue[0]) for clue in wl]).isupper()
    json.dump({"grid": grid, "clues": wl, "rtl": rtl, "allcaps": allcaps}, open("puzzle.json", "w"))
    return wl
