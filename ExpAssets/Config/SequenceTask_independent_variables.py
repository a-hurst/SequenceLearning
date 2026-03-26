from klibs import P
from klibs.KLStructure import FactorSet, Block

import random


# Randomly select 3 of 6 sequences to be practiced sequences

sequences = ['seq1', 'seq2', 'seq3', 'seq4', 'seq5', 'seq6']
training_sequences = random.sample(sequences, 3)

exp_factors = FactorSet({
    'seq_name': training_sequences,
})
test_factors = FactorSet({
    'seq_name': sequences
})

structure = [
    Block(test_factors, label='practice', trials=18),
    Block(exp_factors, label='training', trials=150),
    Block(test_factors, label='test', trials=60),
]
