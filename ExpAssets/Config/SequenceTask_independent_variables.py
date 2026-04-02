from klibs import P
from klibs.KLStructure import FactorSet, Block

import random


# Randomly select 2 of 4 sequences to be practiced sequences

sequences = ['seq1', 'seq2', 'seq3', 'seq4']
training_sequences = random.sample(sequences, 2)

exp_factors = FactorSet({
    'seq_name': training_sequences,
})
prac_factors = FactorSet({
    'seq_name': ['random']
})
test_factors = FactorSet({
    'seq_name': sequences
})

structure = [
    Block(prac_factors, label='practice', trials=30),
    Block(exp_factors, label='training', trials=150),
    Block(test_factors, label='test', trials=60),
]
