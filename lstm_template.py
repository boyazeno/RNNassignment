"""
Minimal character-level LSTM model. Written by Ngoc Quan Pham
Code structure borrowed from the Vanilla RNN model from Andreij Karparthy @karparthy.
BSD License
"""
import numpy as np
from random import uniform
import sys


# Since numpy doesn't have a function for sigmoid
# We implement it manually here
def sigmoid(x):
  return 1 / (1 + np.exp(-x))


# The derivative of the sigmoid function
def dsigmoid(y):
    return y * (1 - y)


# The derivative of the tanh function
def dtanh(x):
    return 1 - x*x


# The numerically stable softmax implementation
def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


# data I/O
data = open('data/input.txt', 'r').read() # should be simple plain text file
chars = list(set(data))
data_size, vocab_size = len(data), len(chars)
print('data has %d characters, %d unique.' % (data_size, vocab_size))
char_to_ix = { ch:i for i,ch in enumerate(chars) }
ix_to_char = { i:ch for i,ch in enumerate(chars) }
std = 0.1


option = sys.argv[1]

# hyperparameters
emb_size = 4
hidden_size = 32  # size of hidden layer of neurons
seq_length = 64  # number of steps to unroll the RNN for
learning_rate = 5e-2
max_updates = 500000

concat_size = emb_size + hidden_size

# model parameters
# char embedding parameters
Wex = np.random.randn(emb_size, vocab_size)*std # embedding layer

# LSTM parameters
Wf = np.random.randn(hidden_size, concat_size) * std # forget gate
Wi = np.random.randn(hidden_size, concat_size) * std # input gate
Wo = np.random.randn(hidden_size, concat_size) * std # output gate
Wc = np.random.randn(hidden_size, concat_size) * std # c term

bf = np.zeros((hidden_size, 1)) # forget bias
bi = np.zeros((hidden_size, 1)) # input bias
bo = np.zeros((hidden_size, 1)) # output bias
bc = np.zeros((hidden_size, 1)) # memory bias

# Output layer parameters
Why = np.random.randn(vocab_size, hidden_size)*0.01 # hidden to output
by = np.zeros((vocab_size, 1)) # output bias


def forward(inputs, targets, memory):
    """
    inputs,targets are both list of integers.
    hprev is Hx1 array of initial hidden state
    returns the loss, gradients on model parameters, and last hidden state
    """

    # The LSTM is different than the simple RNN that it has two memory cells
    # so here you need two different hidden layers
    hprev, cprev = memory

    # Here you should allocate some variables to store the activations during forward
    # One of them here is to store the hiddens and the cells
    xs, wes,zs,hs, cs = {},{},{},{},{}
    f_gate, i_gate, o_gate, c_gate, o, p={},{},{},{},{},{}
    ys={}
    hs[-1] = np.copy(hprev)
    cs[-1] = np.copy(cprev)

    loss = 0
    # forward pass
    for t in range(len(inputs)):
        xs[t] = np.zeros((vocab_size,1)) # encode in 1-of-k representation
        xs[t][inputs[t]] = 1

        # convert word indices to word embeddings
        wes[t] = np.dot(Wex, xs[t])

        # LSTM cell operation
        # first concatenate the input and h
        # This step is irregular (to save the amount of matrix multiplication we have to do)
        # I will refer to this vector as [h X]
        zs[t] = np.row_stack((hs[t-1], wes[t]))

        # YOUR IMPLEMENTATION should begin from here

        # compute the forget gate
        # f_gate = sigmoid (W_f \cdot [h X] + b_f)
        f_gate[t] = sigmoid(Wf.dot(zs[t]) + bf)
        # compute the input gate
        # i_gate = sigmoid (W_i \cdot [h X] + b_i)
        i_gate[t] = sigmoid(Wi.dot(zs[t]) + bi)
        # compute the candidate memory
        # \hat{c} = tanh (W_c \cdot [h X] + b_c])
        c_gate[t] = np.tanh(Wc.dot(zs[t]) + bc)
        # new memory: applying forget gate on the previous memory
        # and then adding the input gate on the candidate memory
        # c_new = f_gate * prev_c + i_gate * \hat{c}
        cs[t] = f_gate[t] * cs[t-1] + i_gate[t] * c_gate[t]
        # output gate
        # o_gate = sigmoid (Wo \cdot [h X] + b_o)
        o_gate[t] = sigmoid(Wo.dot(zs[t]) + bo)
        # new hidden state for the LSTM
        # h = o_gate * tanh(c_new)
        hs[t] = o_gate[t] * np.tanh(cs[t])
        # DONE LSTM
        # output layer - softmax and cross-entropy loss
        # unnormalized log probabilities for next chars

        # o = Why \cdot h + by
        o[t] = Why.dot(hs[t]) + by
        # softmax for probabilities for next chars
        # p = softmax(o)
        p[t] = softmax(o[t])
        # cross-entropy loss
        # cross entropy loss at time t:
        # create an one hot vector for the label y
        ys[t] = np.zeros((vocab_size, 1))
        ys[t][targets[t]] = 1
        # and then cross-entropy (see the elman-rnn file for the hint)
        loss_t = np.sum(-np.log(p[t]) * ys[t])
        loss += loss_t
    # define your activations
    memory = (hs[len(inputs)-1], cs[len(inputs)-1])
    activations = (xs, wes,zs,hs, cs,f_gate, i_gate, o_gate, c_gate, o, p, ys, targets)
    return loss, activations, memory


def backward(activations, clipping=True):
    xs, wes, zs, hs, cs, f_gate, i_gate, o_gate, c_gate, o, p, ys, targets = activations
    # backward pass: compute gradients going backwards
    # Here we allocate memory for the gradients
    dWex, dWhy = np.zeros_like(Wex), np.zeros_like(Why)
    dby = np.zeros_like(by)
    dWf, dWi, dWc, dWo = np.zeros_like(Wf), np.zeros_like(Wi),np.zeros_like(Wc), np.zeros_like(Wo)
    dbf, dbi, dbc, dbo = np.zeros_like(bf), np.zeros_like(bi),np.zeros_like(bc), np.zeros_like(bo)

    # similar to the hidden states in the vanilla RNN
    # We need to initialize the gradients for these variables
    dhnext = np.zeros_like(hs[0])
    dcnext = np.zeros_like(cs[0])
    dhs = {} # Ableitung der hs
    dcs = {} # Ableitung der cs
    dzs = {} # Ableitung der zs
    dwes = {}
    # back propagation through time starts here
    for t in reversed(range(len(inputs))):

        # IMPLEMENT YOUR BACKPROP HERE
        # refer to the file elman_rnn.py for more details
        do = p[t]
        do[targets[t]] -= 1.

        # Ableitung von output Gleichung
        dWhy += do.dot(hs[t].T)
        dhs[t] = Why.T.dot(do) + dhnext
        dby += do

        do_gate = dhs[t]*np.tanh(cs[t])
        dcs[t] = dhs[t] * o_gate[t] * dtanh(cs[t]) + dcnext
        df_gate = dcs[t]*cs[t-1]
        dcs[t-1] = dcs[t]*f_gate[t]
        di_gate = dcs[t]*c_gate[t]
        dc_gate = dcs[t]*i_gate[t]

        # update c
        dcnext = dcs[t-1]

        di_gate_sigmoid = di_gate * dsigmoid(i_gate[t])
        dWi += di_gate_sigmoid.dot(zs[t].T)
        dzs[t] = Wi.T.dot(di_gate_sigmoid)
        dbi += di_gate_sigmoid

        df_gate_sigmoid = df_gate * dsigmoid(f_gate[t])
        dWf += df_gate_sigmoid.dot(zs[t].T)
        dzs[t] += Wf.T.dot(df_gate_sigmoid)
        dbf += df_gate_sigmoid

        do_gate_sigmoid = do_gate * dsigmoid(o_gate[t])
        dWo += do_gate_sigmoid.dot(zs[t].T)
        dzs[t] += Wo.T.dot(do_gate_sigmoid)
        dbo += do_gate_sigmoid

        dc_gate_tanh = dc_gate * dtanh(c_gate[t])
        dWc += dc_gate_tanh.dot(zs[t].T)
        dzs[t] += Wc.T.dot(dc_gate_tanh)
        dbc += dc_gate_tanh

        # update dhnext
        dhs[t-1] = dzs[t][0:hs[t - 1].shape[0],:]
        dhnext = dhs[t-1]

        dwes[t] = dzs[t][hs[t - 1].shape[0]:,:]
        dWex += dwes[t].dot(xs[t].T)


    if clipping:
        # clip to mitigate exploding gradients
        for dparam in [dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby]:
            np.clip(dparam, -5, 5, out=dparam)

    gradients = (dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby)

    return gradients


def sample(memory, seed_ix, n):
    """
    sample a sequence of integers from the model
    h is memory state, seed_ix is seed letter for first time step
    """
    h, c = memory
    x = np.zeros((vocab_size, 1))
    x[seed_ix] = 1
    generated_chars = []
    for t in range(n):
        # IMPLEMENT THE FORWARD FUNCTION ONE MORE TIME HERE
        # BUT YOU DON"T NEED TO STORE THE ACTIVATIONS

        # convert word indices to word embeddings
        wes = np.dot(Wex, x)

        # LSTM cell operation
        # first concatenate the input and h
        # This step is irregular (to save the amount of matrix multiplication we have to do)
        # I will refer to this vector as [h X]
        z = np.row_stack((h, wes))

        f_gate = sigmoid(Wf.dot(z) + bf)
        i_gate = sigmoid(Wi.dot(z) + bi)
        c_gate = np.tanh(Wc.dot(z) + bc)
        c = f_gate * c + i_gate * c_gate
        o_gate = sigmoid(Wo.dot(z) + bo)
        h = o_gate * np.tanh(c)

        o = Why.dot(h) + by
        p = softmax(o)

        # the the distribution, we randomly generate samples:
        ix = np.random.multinomial(1, p.ravel())
        ch = np.zeros((vocab_size, 1))

        index = None
        for j in range(len(ix)):
            if ix[j] == 1:
                index = j
        ch[index] = 1
        generated_chars.append(index)

    return generated_chars


if option == 'train':

    n, p = 0, 0
    n_updates = 0

    # momentum variables for Adagrad
    mWex, mWhy = np.zeros_like(Wex), np.zeros_like(Why)
    mby = np.zeros_like(by) 

    mWf, mWi, mWo, mWc = np.zeros_like(Wf), np.zeros_like(Wi), np.zeros_like(Wo), np.zeros_like(Wc)
    mbf, mbi, mbo, mbc = np.zeros_like(bf), np.zeros_like(bi), np.zeros_like(bo), np.zeros_like(bc)

    smooth_loss = -np.log(1.0/vocab_size)*seq_length # loss at iteration 0
    
    while True:
        # prepare inputs (we're sweeping from left to right in steps seq_length long)
        if p+seq_length+1 >= len(data) or n == 0:
            hprev = np.zeros((hidden_size,1)) # reset RNN memory
            cprev = np.zeros((hidden_size,1))
            p = 0 # go from start of data
        inputs = [char_to_ix[ch] for ch in data[p:p+seq_length]]
        targets = [char_to_ix[ch] for ch in data[p+1:p+seq_length+1]]

        # sample from the model now and then
        if n % 100 == 0:
            sample_ix = sample((hprev, cprev), inputs[0], 200)
            #print(sample_ix)
            print(inputs[0])
            txt = ''.join(ix_to_char[ix] for ix in sample_ix)
            print('----\n %s \n----' % (txt, ))

        # forward seq_length characters through the net and fetch gradient
        loss, activations, memory = forward(inputs, targets, (hprev, cprev))
        gradients = backward(activations)

        hprev, cprev = memory
        dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby = gradients
        smooth_loss = smooth_loss * 0.999 + loss * 0.001
        if n % 100 == 0:
            print('iter %d, loss: %f' % (n, smooth_loss)) # print progress

        # perform parameter update with Adagrad
        for param, dparam, mem in zip([Wf, Wi, Wo, Wc, bf, bi, bo, bc, Wex, Why, by],
                                    [dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWex, dWhy, dby],
                                    [mWf, mWi, mWo, mWc, mbf, mbi, mbo, mbc, mWex, mWhy, mby]):
            mem += dparam * dparam
            param += -learning_rate * dparam / np.sqrt(mem + 1e-8) # adagrad update

        p += seq_length # move data pointer
        n += 1 # iteration counter
        n_updates += 1
        if n_updates >= max_updates:
            break

elif option == 'gradcheck':

    p = 0
    inputs = [char_to_ix[ch] for ch in data[p:p+seq_length]]
    targets = [char_to_ix[ch] for ch in data[p+1:p+seq_length+1]]

    delta = 0.001

    hprev = np.zeros((hidden_size, 1))
    cprev = np.zeros((hidden_size, 1))

    memory = (hprev, cprev)

    loss, activations, _ = forward(inputs, targets, memory)
    gradients = backward(activations, clipping=False)
    dWex, dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWhy, dby = gradients
    fo = open("check.txt", "w")

    for weight, grad, name in zip([Wf, Wi, Wo, Wc, bf, bi, bo, bc, Wex, Why, by], 
                                   [dWf, dWi, dWo, dWc, dbf, dbi, dbo, dbc, dWex, dWhy, dby],
                                   ['Wf', 'Wi', 'Wo', 'Wc', 'bf', 'bi', 'bo', 'bc', 'Wex', 'Why', 'by']):

        str_ = ("Dimensions dont match between weight and gradient %s and %s." % (weight.shape, grad.shape))
        assert(weight.shape == grad.shape), str_

        print(name)
        for i in range(weight.size):
      
            # evaluate cost at [x + delta] and [x - delta]
            w = weight.flat[i]
            weight.flat[i] = w + delta
            loss_positive, _, _ = forward(inputs, targets, memory)
            weight.flat[i] = w - delta
            loss_negative, _, _ = forward(inputs, targets, memory)
            weight.flat[i] = w  # reset old value for this parameter

            grad_analytic = grad.flat[i]
            grad_numerical = (loss_positive - loss_negative) / ( 2 * delta )

            # compare the relative error between analytical and numerical gradients
            rel_error = abs(grad_analytic - grad_numerical) / abs(grad_numerical + grad_analytic)

            if rel_error > 0.01:
                fo.write(name+"\n")
                fo.write('WARNING %f, %f => %e \n' % (grad_numerical, grad_analytic, rel_error))

    fo.close()