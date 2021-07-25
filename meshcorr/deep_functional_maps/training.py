## Standard Lib Imports ##
import os
import sys
import math
import datetime

import numpy as np

## tensorflow ##
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=FutureWarning)
    import tensorflow as tf


cur_dir = os.path.dirname(__file__)
sys.path.insert(1, cur_dir)

import operations as ops
import data_loading as dl
import itertools

'''====================================================================================='''
'''                                       Training                                      '''
'''====================================================================================='''

num_sigs = 600


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def _parse_function(input):

    _features = { 'evecs'  : tf.io.FixedLenFeature([], tf.string),
                  'evecs_t': tf.io.FixedLenFeature([], tf.string),
                  'metric' : tf.io.FixedLenFeature([], tf.string),
                  'sigs'   : tf.io.FixedLenFeature([], tf.string),
                  'N_eigs' : tf.io.FixedLenFeature([],  tf.int64),
                  'N_vert' : tf.io.FixedLenFeature([],  tf.int64),
                  'N_sigs' : tf.io.FixedLenFeature([],  tf.int64) }

    parsed_features = tf.io.parse_single_example(input, features = _features)

    N_eigs  = tf.cast(parsed_features['N_eigs'], tf.int32)
    N_vert  = tf.cast(parsed_features['N_vert'], tf.int32)
    N_sigs  = tf.cast(parsed_features['N_sigs'], tf.int32)

    evecs   = tf.reshape(tf.io.decode_raw(parsed_features[  "evecs"], tf.float32), [N_vert, N_eigs])
    evecs_t = tf.reshape(tf.io.decode_raw(parsed_features["evecs_t"], tf.float32), [N_eigs, N_vert])
    metric  = tf.reshape(tf.io.decode_raw(parsed_features[ "metric"], tf.float32), [N_vert, N_vert])
    sigs    = tf.reshape(tf.io.decode_raw(parsed_features[   "sigs"], tf.float32), [N_vert, N_sigs])

    return evecs, evecs_t, sigs, metric


class ensembleTrainer:

    def __init__(self, files, lr = 1e-3, bs = 1, chkpt_name = None):
        self.func      =  ops.correspondenceMatrix(num_sigs, training = True)
        self.loss      =  tf.keras.metrics.Mean(name='train_loss')
        self.optimiser =  tf.keras.optimizers.Adam(learning_rate = lr)
        self.datasets  =  [tf.data.TFRecordDataset(fin).map(_parse_function).shuffle(buffer_size=128).batch(bs) for fin in files]

        current_time  =  datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_dir = os.path.join('logs/gradient_tape/' + current_time)
        self.summary_writer =  tf.summary.create_file_writer(log_dir)

        if chkpt_name is not None:
            weight_path = os.path.join(cur_dir, 'checkpoints', chkpt_name )
            self.func.load_weights(weight_path)
            print("Weights loaded.")

        return None

    @tf.function
    def train_step(self, x, y):
        e_x, et_x, s_x, g_x = x
        e_y, et_y, s_y, g_y = y
        with tf.GradientTape() as tape:
            C     =  self.func([s_x, s_y], [et_x, et_y])
            P     =  ops.softCorrespondenceEnsemble(C, et_x, e_y)
            loss  =  ops.geodesicErrorEnsemble(P, g_x, g_y)
            grads =  tape.gradient(loss, self.func.trainable_variables)
            self.optimiser.apply_gradients(zip(grads, self.func.trainable_variables))
        self.loss(loss)
        return None


    def train(self, EPOCHS, chkpt_name):
        best = -1
        for epoch in range(EPOCHS):
            for dataset in self.datasets:
                for x,y in pairwise(dataset):
                    try:
                        self.train_step(x,y)
                    except:
                        print("Error caught.")
            epoch_loss = self.loss.result()
            print('Epoch {}, Loss: {}'.format(epoch + 1, 100*epoch_loss))
            with self.summary_writer.as_default():
                tf.summary.scalar('loss', epoch_loss, step=epoch)
            self.loss.reset_states()
            if (1 < epoch and epoch_loss < best):
                self.func.save_weights('./checkpoints/{0}'.format(chkpt_name))
                best = epoch_loss
            if (epoch == 1):
                best = epoch_loss

        return None




if __name__ == "__main__":
    import sys
    import os
    import json

    cur_dir = os.path.dirname(__file__)
    sys.path.insert(1,os.path.join(cur_dir,'..','..','tools'))

    #types   =  np.load(os.path.join(dir_in, 'types.npy'))
    input = ['./data/early_hind_wt_limbs.tfrecords']
    trainer = ensembleTrainer(files = input, lr = 1e-4, bs = 1, chkpt_name = None)
    trainer.train(EPOCHS = 500, chkpt_name = 'early_hind_wt_limbs')

    #for type in types:
    #    print('\n\n' + type + '\n\n')
    #    fjson = os.path.join(dir_in, 'configs', type + '.json')
    #    with open(fjson) as file:
    #        config = json.load(file)
