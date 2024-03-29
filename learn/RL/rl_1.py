# based on RL/openai_gym/nchain

import gym
import time
import numpy as np
import learn.airfoil_dynamics.ct_plot.vawt_blade as vb
import math
import learn.airfoil_dynamics.ct_plot.base_calculus as bc
import pandas as pd
import matplotlib.pyplot as plt


class VawtEnvironment:

    def __init__(self, blade, steps=10000):
        self.blade = blade
        self.steps = steps
        # current state of blade (theta, pitch)
        self.data = self.tf_data()
        self.theta_num = self.data.shape[0]
        self.pitch_num = self.data.shape[1]
        self.reset()

    def reset(self):
        self.position = (0, round(self.data.shape[1]/2))
        self.current_step = 0
        return self.position

    def step(self, action):
        self.current_step += 1
        self.position = (self.get_new_theta(), self.get_new_pitch(action))
        try:
            reward = self.data.iloc[self.position[0], self.position[1]]
        except IndexError:
            pass
        done = False
        if self.current_step > self.steps:
            done = True
        debug = None
        return self.position, reward, done, debug

    def tf_data(self):
        wind_direction = 0
        wind_speed = 6
        rotor_speed = 6
        wind_vector = bc.get_wind_vector(wind_direction, wind_speed)
        theta_range = [x * math.tau / 360 for x in range(-180, 180, 5)]
        pitch_range = [x * math.tau / 360 for x in range(-180, 180, 5)]
        thetas = []
        for theta in theta_range:
            theta_ct_polar = [blade.get_tangential_force(wind_vector, rotor_speed, theta, pitch) for pitch in pitch_range]
            thetas.append(theta_ct_polar)

        df = pd.DataFrame(thetas, index=theta_range, columns=pitch_range)
        return df

    def get_new_theta(self):
        new_theta = self.position[0] + 1
        if new_theta >= self.data.shape[0]:
            new_theta = new_theta - self.data.shape[0]
        return new_theta

    def get_new_pitch(self, delta):
        new_pitch = self.position[1] + delta
        if new_pitch >= self.data.shape[1]:
            new_pitch = new_pitch - self.data.shape[1]
        if new_pitch < 0:
            new_pitch = self.data.shape[1] + new_pitch
        return new_pitch


def naive_sum_reward_agent(env, num_episodes=500):
    # state is rotor theta and blade pitch
    # next state is new theta and pitch
    # there are theta * pitch 360*360= 129600 states
    # assuming theta 2pi range and 5 degrees step = 120 positions
    # and pitch (-1,1) range and 5 degree step = 120 positions
    # we get 120*120 = 14400 states
    # an action is a transition to theta + 1 and pitch + (angle from range of angle changes)
    # a reward is tangential force generated by blade in current position
    # assume maximum change of blade pitch in index length - 5 indicates pitch acn change as much as 5 columns back or forth

    max_pitch_change = 3

    # create r table of size (num of theta samples+num of pitch samples)xnumber of possible new pitch values
    r_table = np.zeros((env.data.size, max_pitch_change * 2 + 1))
    indexes = [range(env.data.shape[0]), range(env.data.shape[1])]
    m_index = pd.MultiIndex.from_product(indexes, names=['theta', 'pitch'])
    r_df = pd.DataFrame(r_table, index=m_index, columns=range(-max_pitch_change, max_pitch_change+1))
    # identical in size as theta-pitch dataframe
    coverage_df = env.data.copy()
    # zero coverage df
    for col in coverage_df.columns:
        coverage_df[col].values[:] = 0

    for g in range(num_episodes):
        s = env.reset()
        done = False
        while not done:
            # current state multiindex
            s_index = (s[0], s[1])
            # update coverage
            coverage_df.iloc[s_index] += 1
            # if there arent yet rewards for given state pick random action
            if np.sum(r_df.loc[s_index]) == 0:
                # make a random selection of actions
                a = np.random.randint(-max_pitch_change, max_pitch_change+1)
            else:
                # select the action with highest cummulative reward
                # as an action pick name of column that is has highest value for given state
                a = r_df.columns.values[np.argmax(r_df.loc[s_index])]
                # if a not in r_df.columns.values:
                #     a = np.random.randint(-max_pitch_change, max_pitch_change + 1)

            new_s, r, done, _ = env.step(a)
            try:
                r_df.loc[s_index, a] += r
            except KeyError:
                pass
            s = new_s
        print("Episode {}".format(g))
        # plot coverage
        xx, yy = np.meshgrid(env.data.index.values, env.data.columns.values)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.title.set_text('f')
        # ax.set_xlabel('x')
        # ax.set_ylabel('y')
        ax.set_xlabel('theta')
        ax.set_ylabel('pitch')
        ax.plot_surface(xx, yy, np.transpose(coverage_df), rstride=1, cstride=1, cmap='viridis', edgecolor='none')

        plt.show()
    return r_df


def q_learning_with_table(env, num_episodes=500):

    y = 0.95
    lr = 0.8

    max_pitch_change = 5

    # create r table of size (num of theta samples+num of pitch samples)xnumber of possible new pitch values
    q_table = np.zeros((env.data.size, max_pitch_change * 2 + 1))
    indexes = [range(env.data.shape[0]), range(env.data.shape[1])]
    m_index = pd.MultiIndex.from_product(indexes, names=['theta', 'pitch'])
    q_df = pd.DataFrame(q_table, index=m_index, columns=range(-max_pitch_change, max_pitch_change+1))
    # identical in size as theta-pitch dataframe
    coverage_df = env.data.copy()
    # zero coverage df
    for col in coverage_df.columns:
        coverage_df[col].values[:] = 0

    for i in range(num_episodes):
        s = env.reset()
        done = False
        while not done:
            # current state multiindex
            s_index = (s[0], s[1])
            # update coverage
            coverage_df.iloc[s_index] += 1
            # if there arent yet rewards for given state pick random action
            if np.sum(q_df.loc[s_index]) == 0:
                # make a random selection of actions
                a = np.random.randint(-max_pitch_change, max_pitch_change + 1)
            else:
                # select the action with highest cummulative reward
                # as an action pick name of column that is has highest value for given state
                a = q_df.columns.values[np.argmax(q_df.loc[s_index])]

            new_s, r, done, _ = env.step(a)
            q_df.loc[s_index, a] += r + lr*(y*np.max(q_df.loc[(new_s[0], new_s[1]), :]) - q_df.loc[s_index, a])
            s = new_s
        print("Episode {}".format(i))
        # plot coverage
        xx, yy = np.meshgrid(env.data.index.values, env.data.columns.values)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.title.set_text('f')
        # ax.set_xlabel('x')
        # ax.set_ylabel('y')
        ax.set_xlabel('theta')
        ax.set_ylabel('pitch')
        ax.plot_surface(xx, yy, np.transpose(coverage_df), rstride=1, cstride=1, cmap='viridis', edgecolor='none')

        plt.show()
    return q_df


def eps_greedy_q_learning_with_table(env, num_episodes=500):

    y = 0.95
    eps = 0.5
    lr = 0.8
    decay_factor = 0.999

    max_pitch_change = 5

    # create r table of size (num of theta samples+num of pitch samples)xnumber of possible new pitch values
    q_table = np.zeros((env.data.size, max_pitch_change * 2 + 1))
    indexes = [range(env.data.shape[0]), range(env.data.shape[1])]
    m_index = pd.MultiIndex.from_product(indexes, names=['theta', 'pitch'])
    q_df = pd.DataFrame(q_table, index=m_index, columns=range(-max_pitch_change, max_pitch_change+1))
    # identical in size as theta-pitch dataframe
    coverage_df = env.data.copy()
    # zero coverage df
    for col in coverage_df.columns:
        coverage_df[col].values[:] = 0

    for i in range(num_episodes):
        s = env.reset()
        eps *= decay_factor
        done = False
        while not done:
            # current state multiindex
            s_index = (s[0], s[1])
            # update coverage
            coverage_df.iloc[s_index] += 1
            # if there arent yet rewards for given state
            # or randomly decide pick random action
            if np.sum(q_df.loc[s_index]) == 0 or np.random.random() < eps:
                # make a random selection of actions
                a = np.random.randint(-max_pitch_change, max_pitch_change + 1)
            else:
                # select the action with highest cummulative reward
                # as an action pick name of column that is has highest value for given state
                a = q_df.columns.values[np.argmax(q_df.loc[s_index])]

            new_s, r, done, _ = env.step(a)
            q_df.loc[s_index, a] += r + lr*(y*np.max(q_df.loc[(new_s[0], new_s[1]), :]) - q_df.loc[s_index, a])
            s = new_s
        print("Episode {}".format(i))
    # plot coverage
    xx, yy = np.meshgrid(env.data.index.values, env.data.columns.values)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.title.set_text('f')
    # ax.set_xlabel('x')
    # ax.set_ylabel('y')
    ax.set_xlabel('theta')
    ax.set_ylabel('pitch')
    ax.plot_surface(xx, yy, np.transpose(coverage_df), rstride=1, cstride=1, cmap='viridis', edgecolor='none')

    # plt.show()
    plt.savefig('foo.png', bbox_inches='tight')
    return q_df, coverage_df


airfoil_dir = '/home/aa/vawt_env/learn/AeroDyn polars/naca0018_360'
# vb.VawtBlade(blade chord, airfoil_dir, rotor_radius)
blade = vb.VawtBlade(0.2, airfoil_dir, 1)
env = VawtEnvironment(blade)
# table = naive_sum_reward_agent(env)
# q_table = q_learning_with_table(env)
q_df, coverage_df = eps_greedy_q_learning_with_table(env, 20)
# save coverage table
coverage_df.to_csv("eps_greedy_q_learning_old.csv")
# print(table)
# started 9:38 taking 100000 steps stopped about 9:41 - 3 minutes long