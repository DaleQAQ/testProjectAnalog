import random

import numpy as np
import torch.nn as nn
import torch
import torch.optim as optim
import torch.nn.functional as F
class TestNode(object):
    def __init__(self, cost, faultIsolationArray):
        """
        :param cost: The cost of each test node
        :param faultIsolationArray: The accuracy list of faults that can be Isolated
        """
        self.cost = cost
        self.faultIsolationArray = faultIsolationArray

class AUTODL:
    def __init__(self,git):
        self.git = git
# Neural Network Model for Q-Learning
# This model will approximate the Q-Values for each possible action(node to pick next)
# This network has three fully connected layers with ReLU activations

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        """
        Initialize the Deep Q-Network with the input_size representing the number of test nodes and output_size representing
        the number of possible actions (next node to pick)
        :param input_size: the number of test nodes
        :param output_size: the next test node to pick
        """
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, output_size)
    def forward(self, x):
        """
        :param x: input current state
        :return: Q-value
        """
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# Test Nodes Selection(TNS)Agent Setup
# This agent interacts with the environment, makes decisions, stores experiences, and learns from them.
# The agent uses Q-learning to find the optimal node that minimizes the cost and maximize the isolated faults number.
class TNSAgent:
    def __init__(self, num_nodes, gamma=0.99, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01, lr=0.001):
        """
        :param num_nodes: the number of nodes
        :param gamma: discount factor (how much future rewards are considered)
        :param epsilon: initial exploration rate (for epsilon-greedy strategy)
        :param epsilon_decay: how quickly exploration rate decays
        :param epsilon_min: minimum exploration rate
        :param lr: learning rate for optimizer
        """
        self.num_nodes = num_nodes
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.memory = []    # number of buffer to store experiences
        self.batch_size = 32  # number of experiences to sample for training
        self.memory_capacity = 10000    # max capacity of memory buffer
        self.lr = lr
        self.q_network = DQN(num_nodes, num_nodes)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=self.lr)
        self.criterion = nn.MSELoss()

    def store_experience(self, state, action, reward, next_state, done):
        """
        Store the agent's experience(state, action, reward, next_state, done) in memory for experience replay.
        If memory exceeds its capacity, the oldest experience is removed.
        """
        if len(self.memory) > self.memory_capacity:
            self.memory.pop(0)
        self.memory.append((state, action, reward, next_state, done))

    def choose_action(self, state):
        """
        Choose an action(next city to visit) using epsilon-greedy strategy.
        - With probability epsilon, choose a random action(exploration).
        - Otherwise, choose the action with the highest Q-value(exploitation)
        """
        if np.random.rand() < self.epsilon:
            return random.randint(0, self.num_nodes - 1)
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            with torch.no_grad():
                q_values = self.q_network(state_tensor)
            return torch.argmax(q_values).item()

    def train(self):
        """
        Train the Q-network using the experiences stored in memory.
        For each experience, update the Q-value towards the target value:
        Q_target = reward + gamma * max(Q(next_state)) if not done.
        """
        if len(self.memory) < self.batch_size:
            return   # Don't train if there aren't enough experiences in memory
        # Sample a batch of experiences randomly from memory
        batch = random.sample(self.memory, self.batch_size)
        for state, action, reward, next_state, done in batch:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0)
            target = reward
            if not done:
                target = reward + self.gamma * torch.max(self.q_network(next_state_tensor))
                q_value = self.q_network(state_tensor)[0, action]
                loss = self.criterion(q_value, torch.tensor(target))

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

            if self.epilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay

class TNSEnvironment:
    def __init__(self, nodes):
        """
        Initialize the environment with a list of cities.
        It also tracks the current state(nodes picked), total cost, and the current node picked.
        """
        self.nodes = nodes
        self.num_nodes = len(nodes)
        self.current_state = []   # The current state will store which nodes have been picked
        self.current_node = None
        self.picked = []
        self.total_faults = 13
        self.total_cost = 0
        self.total_fault_isolated = []
        self.total_fault_isolated_num = 0
    def reset(self):
        """
        Reset the environment for a new episode.
        The agent starts from a random node, and no nodes have been  picked yet.
        """
        self.current_state = np.zeros(self.num_nodes)
        self.current_node = random.randint(0, self.num_nodes - 1)
        self.picked = []
        self.total_fault_isolated = np.zeros(self.total_faults)
        return self.current_state
    def step(self,action):
        """
        Take a step in the environment by picking a node (the action).
        - If the agent picking a node again, it gets a negative reward.
        - Otherwise, the reward is the negative cost of the picked node.
        - The episode ends when all faults are isolated (done=True).
        :param action: a index of node
        """
        if action in self.picked:
            reward = -10
        else:
            reward = - self.nodes[action].cost
            self.total_fault_isolated += self.nodes[action].faultIsolationArray
            self.picked.append(action)
            self.total_cost += abs(reward)
        self.current_node = action
        self.current_state[action] = 1
        is_all_one = lambda lst: all(x == 1 for x in lst)
        self.total_fault_isolated_num = sum(self.total_fault_isolated)
        done = is_all_one(self.total_fault_isolated)

        return self.current_state, reward, done

# Function to train the agent for multiple episode of interaction with the environment
def train_tns_agent(nodes, episodes = 1000):
    """
    Train the TNS agent using Q-learning for a given number of episodes.
    The agent interacts with the environment, learns from its experiences, and improves its policy.
    """
    env = TNSEnvironment(nodes)
    agent = TNSAgent(num_nodes= len(nodes))

    for episode in range(episodes):
        state = env.reset()
        done = False
        total_cost = 0

        while not done:
            action = agent.choose_action(state)
            next_state, reward, done = env.step(action)
            agent.store_experience(state, action, reward, next_state, done)
            state = next_state
            total_cost += abs(reward)
        print(f"Episode {episode+1}, Total Cost: {total_cost}, Total Fault Isolation: {env.total_fault_isolated_num}")