"""A link must survive translation (written before the prompt change).

An eval run asked a question in Chinese and the model rewrote the link text in 2 of 3 answers
("Inkwell Books：20% 折扣" with a full-width colon) although the rules already said not to translate it. The
address was still right, but the text was no longer what the server wrote. The rule now says what to translate.
"""
import re

from app.assistant import build_system_prompt


def links_rule():
    prompt = build_system_prompt(None)
    return " ".join(prompt[prompt.index("LINKS"):prompt.index("STYLE")].split())


def test_the_rule_still_says_to_copy_link_markdown_exactly():
    rule = links_rule()
    assert re.search(r"copy link_markdown exactly as given, character for character", rule, re.I)
    assert re.search(r"do not edit, shorten or translate it", rule, re.I)


def test_the_rule_says_it_holds_in_every_language_and_what_to_translate_instead():
    rule = links_rule()
    assert re.search(r"this holds when you answer in another language", rule, re.I)
    assert re.search(r"translate the words around the link, never the link itself", rule, re.I)
    assert re.search(r"its text stays in English", rule, re.I)


def test_the_rule_still_forbids_any_other_address():
    assert re.search(r"never write any other link", links_rule(), re.I)
