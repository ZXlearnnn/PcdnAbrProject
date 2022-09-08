import argparse


def get_args():
    parser = argparse.ArgumentParser(description='EdgeServerConfiguration')

    # The cache configuration and cache policy configuration
    parser.add_argument('--max-cache-size', type=float, default=1.006,
                        help='GB, The max cache size of the edge server')
    parser.add_argument('--cache-path', type=str, default='/home/maxt/EdgeServer/videodata',
                        help='The path of the cache content')
    parser.add_argument('--cache-margin', type=int, default=10,
                        help='MB, start eviction policy when > [max_cache_size - cache_margin]')
    parser.add_argument('--lru-sample-num', type=int, default=5,
                        help='The random sample number according to the lru policy')
    parser.add_argument('--debug', default=False,
                        help='The debug mode will output some log information.')
    parser.add_argument('--pre-chunk-in-edge-num', type=int, default=10,
                        help='The chunk can be saved in the edge cache with can reduce the '
                             'initial rebuffering')

    # The configuration of the seed clients
    parser.add_argument('--min-upload-capacity', type=int, default=5,
                        help='Mbps, if the estimated_available_bw is lower than this value, '
                             'the client will not be regarded as the seed client anymore.')
    parser.add_argument('--max-seed-client-num', type=int, default=3,
                        help='The max num of seed clients who offer the service.')

    # The configuration of the measurement
    parser.add_argument('--throughput-measurement-length', type=int, default=20,
                        help='The default length of the throughput measurement')
    parser.add_argument('--average-throughput-data-number', type=int, default=5,
                        help='The number of throughput value that be taken into account to predict the throughput')

    # The configuration of the edge-side ABR
    parser.add_argument('--urgent-buffer', type=int, default=6,
                        help='When the edge justify that the current buffer is lower than the urgent buffer, the edge'
                             'can not request for the target track')

    args = parser.parse_args()

    return args


def get_steward_args():
    parser = argparse.ArgumentParser(description='StewardEdgeServerConfiguration')

    # The configuration of online A3C network
    parser.add_argument('--actor-lr', type=float, default=5e-4,
                        help='learning rate of actor network (default: 0.0008)')
    parser.add_argument('--critic-lr', type=float, default=1e-3,
                        help='learning rate of critic network (default: 0.001)')
    parser.add_argument('--s-dim', type=int, default=33, help='The length of the state space')
    parser.add_argument('--a-dim', type=int, default=10, help='The length of the action space')
    parser.add_argument('--gamma', type=float, default=0.9,
                        help='discount factor for rewards (default: 0.99)')
    parser.add_argument('--entropy-coef', type=float, default=0.01,
                        help='entropy term coefficient (default: 0.00001)')
    parser.add_argument('--num-steps', type=int, default=10,
                        help='number of forward steps in A3C (default: 10)')
    parser.add_argument('--summary-dir', default='/home/maxt/DjangoEdge145/Steward/a3c_results',
                        help='the path to save model')
    parser.add_argument('--nn_model',
                        default='/home/maxt/DjangoEdge145/StewardApp/a3c_results/model_saver/offline_exp/tmp_test/nn_model_ep_474000.ckpt',
                        help='the path of the pre-trained model.')
    parser.add_argument('--model-save-interval', default=2000,
                        help='save the model in how many epochs')
    parser.add_argument('--log-dir', default='/home/maxt/DjangoEdge145/Steward/a3c_results/log',
                        help='the path to save logs')
    parser.add_argument('--rand-range', default=1000,
                        help='used for random sample to determine action')
    # State configuration
    parser.add_argument('--delay-count', default=6, type=int, help='imply the time horizon we take into account')
    # The configuration of the env
    parser.add_argument('--default-track', default=1, type=int, help='The default action of the agent')
    # For online test
    parser.add_argument('--start-timestamp', default=0, help='The start time stamp of the experiment')
    parser.add_argument('--test-reward-dir', default='/home/maxt/DjangoEdge145/StewardApp/test_reward_data/a3c',
                        help='The reward during testing RL model')
    parser.add_argument('--test-id', default=6, help='We may test many times, the folder name')
    parser.add_argument('--test-model-epoch-id', default=0, help='To mark the name of model')

    args = parser.parse_args()

    return args
