# Hoang M. Le
# California Institute of Technology
# hmle@caltech.edu
# 
# Simple testing of trained subgoal models
# ===================================================================================================================

import os

os.environ['PYTHONHASHSEED'] = '0'

import argparse
import sys
import time
import numpy as np
import tensorflow as tf
from collections import namedtuple, deque
from environment_atari import ALEEnvironment
from hybrid_rl_il_agent_atari import Agent
from hybrid_model_atari import Hdqn
from simple_net import Net
from PIL import Image
from tensorboard import TensorboardVisualizer
from os import path
import time
import planner
import math, random
from hyperparameters_new import *
import pickle as pk


def pause():
    os.system('read -s -n 1 -p "Press any key to continue...\n"')

def generateplan():
    clingopath = "clingo"
#    initial = "initial.lp"
    goal = "goal.lp"
    planning = "montezuma_basic.lp"
    qvalue = "q.lp"
    constraint = "constraint.lp"
    return planner.compute_plan(clingopath = clingopath, goal=goal, planning=planning, qvalue=qvalue, constraint = constraint, printout=True) 

def calculateplanquality(ro_table,stateaction):
    planquality = 0
    for (state,action) in stateaction:
        planquality += int(math.floor(ro_table[state,action]))
    return planquality

def generate_rovalue_from_table(env,ro_table_lp,ro_table):
#    print "output qvalues"
    qfile = open("q.lp","w")
    for (state,action) in ro_table_lp:
        logical_state = stateRemapping(state)
        logical_action = actionRemapping(action)
        qrule = "ro("+logical_state+","+logical_action+","+str(int(math.floor(ro_table[state,action])))+").\n"
        qfile.write(qrule)
    qfile.close()

def generate_goal_file(planquality):
#    print "output new goal file"
    goalfile = open("goal.lp","w")
    goalfile.write("#program check(k).\n")
#    goalfile.write(":- not at(key,k), query(k).\n")
    goalfile.write(":- query(k), cost(C,k), C <= "+str(planquality)+".\n")
    goalfile.write(":- query(k), cost(0,k).")
    goalfile.close()

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def cleanupconstraint():
    open('constraint.lp', 'w').close()

def updateconstraint(state_ind,action_ind):
    state = stateRemappingWithTimeStamps(state_ind)
    action = actionRemappingWithTimeStamps(action_ind)
    constraint = ":-"+state+","+action+".\n"
    f = open("constraint.lp","a")
    f.write("#program step(k).\n")
    f.write(constraint)
    f.close()

def selectSubGoal(plantrace,i): 
    currentunit = plantrace[i]
    currentfluent = currentunit[2]
    nextunit = plantrace[i+1]
    nextfluent = nextunit[2]
    # subgoal networks, mapped from every possible symbolic transition
    # currently we only train for good ones. Will add useless(difficult) ones later.
    # make sure the goal number here maps correctly to bounding boxes in environment_atari.py

    if ("at(plat1)" in currentfluent) and ("at(lower_right_ladder)" in nextfluent) and ("picked(key)" not in nextfluent):
        return 0
    if ("at(lower_right_ladder)" in currentfluent) and ("at(devilleft)" in nextfluent):
        return 1
    if ("at(devilleft)" in currentfluent) and ("at(key)" in nextfluent):
        return 2
    if ("at(key)" in currentfluent) and ("at(lower_left_ladder)" in nextfluent):
        return 3
    if ("at(lower_left_ladder)" in currentfluent) and ("at(lower_right_ladder)" in nextfluent):
        return 4
    if ("at(lower_right_ladder)" in currentfluent) and ("at(plat1)" in nextfluent):
        return 5
    if ("at(plat1)" in currentfluent) and ("at(right_door)" in nextfluent):
        return 6
    return -1

def obtainStateAction(plantrace,i):
    unit = plantrace[i]
    action = unit[1]
    fluent = unit[2]
    return stateMapping(fluent),actionMapping(action)

def actionMapping(action):
    if 'move(lower_right_ladder)' in action:
        return 0
    if 'move(lower_left_ladder)' in action:
        return 1
    if 'move(key)' in action:
        return 2
    if 'move(right_door)' in action:
        return 3
    if 'move(devilleft)' in action:
        return 4
    if 'move(plat1)' in action:
        return 5

def stateMapping(fluent): # symbolic state to goal mapping
    if ("at(lower_right_ladder)" in fluent) and ("picked(key)" not in fluent):
        return 0
    if ("at(key)" in fluent) and ("picked(key)" in fluent):
        return 1
    if ("at(lower_right_ladder)" in fluent) and ("picked(key)" in fluent):
        return 2
    if ("at(right_door)" in fluent) and ("picked(key)" in fluent):
        return 3
    if ("at(right_door)" in fluent) and ("picked(key)" not in fluent):
        return 4
    if ("at(devilleft)" in fluent):
        return 5
    if ("at(plat1)" in fluent) and ("picked(key)" in fluent):
        return 6
    if ("at(lower_left_ladder)" in fluent) and ("picked(key)" in fluent):
        return 7
    if ("at(lower_left_ladder)" in fluent) and ("picked(key)" not in fluent):
        return 8
    return -1

def actionRemapping(action_ind):
    if action_ind == 0:
        return 'move(lower_right_ladder)'
    if action_ind == 1:
        return 'move(lower_left_ladder)'
    if action_ind == 2:
        return 'move(key)'
    if action_ind == 3:
        return 'move(right_door)'
    if action_ind == 4:
        return 'move(devilleft)'
    if action_ind == 5:
        return 'move(plat1)'
    return ''

def stateRemapping(fluent_ind): # symbolic state to goal mapping
    if fluent_ind == -1:
        return 'at(plat1)'
    if fluent_ind == 0:
        return 'at(lower_right_ladder)'
    elif fluent_ind == 1:
        return '(at(key),picked(key))'
    elif fluent_ind == 2:
        return '(at(lower_right_ladder),picked(key))'
    elif fluent_ind == 3:
        return '(at(right_door),picked(key))'
    elif fluent_ind == 4:
        return 'at(right_door)'
    elif fluent_ind == 5:
        return 'at(devilleft)'
    elif fluent_ind == 6:
        return '(at(plat1),picked(key))'
    elif fluent_ind == 7:
        return '(at(lower_left_ladder),picked(key))'
    elif fluent_ind == 8:
        return 'at(lower_left_ladder)'
    return ''

def actionRemappingWithTimeStamps(action_ind):
    if action_ind == 0:
        return 'move(lower_right_ladder,k)'
    if action_ind == 1:
        return 'move(lower_left_ladder,k)'
    if action_ind == 2:
        return 'move(key,k)'
    if action_ind == 3:
        return 'move(right_door,k)'
    if action_ind == 4:
        return 'move(devilleft,k)'
    if action_ind == 5:
        return 'move(plat1,k)'
    return ''

def stateRemappingWithTimeStamps(fluent_ind): # symbolic state to goal mapping
    if fluent_ind == -1:
        return 'at(plat1,k)'
    if fluent_ind == 0:
        return 'at(lower_right_ladder,k)'
    elif fluent_ind == 1:
        return 'at(key,k),picked(key,k)'
    elif fluent_ind == 2:
        return 'at(lower_right_ladder,k),picked(key,k)'
    elif fluent_ind == 3:
        return 'at(right_door,k),picked(key,k)'
    elif fluent_ind == 4:
        return 'at(right_door,k)'
    elif fluent_ind == 5:
        return 'at(devilleft,k)'
    elif fluent_ind == 6:
        return 'at(plat1,k),picked(key,k)'
    elif fluent_ind == 7:
        return 'at(lower_left_ladder,k),picked(key,k)'
    elif fluent_ind == 8:
        return 'at(lower_left_ladder,k)'
    return ''

def throwdice(threshold):
    rand =  random.uniform(0,1)
    if rand < threshold:
        return True
    else:
        return False

def obtainedKey(previoustate,nextstate):
    if ("picked(key)" not in previoustate) and ("picked(key)" in nextstate):
        return True
    else:
        return False

def openDoor(previoustate,nextstate):
    if ("picked(key)" in previoustate) and ("at(right_door)" not in previoustate) and ("picked(key)" in nextstate) and ("at(right_door)" in nextstate):
        return True
    else:
        return False

def main():

    actionMap = [0, 1, 2, 3, 4, 5, 11, 12]

    actionExplain = ['no action', 'jump', 'up', 'right', 'left', 'down', 'jump right', 'jump left']

    goalExplain = ['lower right ladder', 'jump to the left of devil', 'key', 'lower left ladder',
                   'lower right ladder', 'central high platform', 'right door'] #7

    Num_subgoal = len(goalExplain)
    subgoal_success_tracker = [[] for i in range(Num_subgoal)] # corresponds to the 7 subgoals
    subgoal_trailing_performance = [0, 0, 0, 0, 0, 0, 0] # corresponds to the 7 subgoals
    random_experience = [deque(), deque(), deque(), deque(), deque(), deque(), deque()]
    kickoff_lowlevel_training = [False, False, False, False, False, False, False]

    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="montezuma_revenge.bin")
    parser.add_argument("--display_screen", type=str2bool, default=True)
    parser.add_argument("--frame_skip", default=4)
    parser.add_argument("--color_averaging", default=True)
    parser.add_argument("--random_seed", default=0)
    parser.add_argument("--minimal_action_set", default=False)
    parser.add_argument("--screen_width", default=84)
    parser.add_argument("--screen_height", default=84)
    parser.add_argument("--load_weight", default=False)
    parser.add_argument("--use_sparse_reward", type=str2bool, default=True)
    args = parser.parse_args()
    ActorExperience = namedtuple("ActorExperience", ["state", "goal", "action", "reward", "next_state", "done"])
    MetaExperience = namedtuple("MetaExperience", ["state", "goal", "reward", "next_state", "done"])
    annealComplete = False
    saveExternalRewardScreen = True

    env = ALEEnvironment(args.game, args)
    # print "agent loc:",env.getAgentLoc(env.getScreenRGB())

    # Initilize network and agent

    hdqn = Hdqn(GPU)
    hdqn1 = Hdqn(GPU)
    hdqn2 = Hdqn(GPU)
    hdqn3 = Hdqn(GPU)
    hdqn4 = Hdqn(GPU)
    hdqn5 = Hdqn(GPU)
    hdqn6 = Hdqn(GPU)

    hdqn_list = [hdqn, hdqn1, hdqn2, hdqn3, hdqn4, hdqn5, hdqn6]

    Num_hdqn = len(hdqn_list) #7 subgoal

    with open('./summary_v1/data.pkl', 'rb') as f:
        data = pk.load(f)
    
    hdqn.loadWeight('0')
    hdqn1.loadWeight('1')
    hdqn2.loadWeight('2')
    hdqn3.loadWeight('3')
    hdqn4.loadWeight('4')
    hdqn5.loadWeight('5')
    hdqn6.loadWeight('6')

    # for i in range(Num_hdqn):
    #     if i not in goal_to_train:
    #         hdqn_list[i].loadWeight(i) # load the pre-trained weights for subgoals that are not learned?
    #         kickoff_lowlevel_training[i] = True # switch this off


    agent = Agent(hdqn, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=1000, controllerMemCap=EXP_MEMORY, explorationSteps=50000, trainFreq=TRAIN_FREQ, hard_update=1000)
    agent1 = Agent(hdqn1, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    agent2 = Agent(hdqn2, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    agent3 = Agent(hdqn3, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    agent4 = Agent(hdqn4, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    agent5 = Agent(hdqn5, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    agent6 = Agent(hdqn6, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ, hard_update=HARD_UPDATE_FREQUENCY)
    # agent7 = Agent(hdqn7, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ,hard_update=HARD_UPDATE_FREQUENCY)
    # agent8 = Agent(hdqn7, range(nb_Action), range(Num_subgoal), defaultNSample=BATCH, defaultRandomPlaySteps=20000, controllerMemCap=EXP_MEMORY, explorationSteps=200000, trainFreq=TRAIN_FREQ,hard_update=HARD_UPDATE_FREQUENCY)
    agent_list = [agent, agent1, agent2, agent3, agent4, agent5, agent6]

    for agent in agent_list:
        agent.learning_done = True


    episodeCount = 0
    stepCount = 0

    episodeCount = 0

    plantrace = []
    ro_table_lp = []

    episodeCumulativeRew = []

    nS = 14  # 6 locations, doubled with key picked, in total, 8 states, 1 good terminal (-2), 1 bad terminate (-3)
    nA = 6  # move to right ladder, move to key, move to left ladder, move to door, move to left of devil, move to initial

    R_table = data['R_table']
    ro_table = data['ro_table']
    ro_table_lp = data['ro_table_lp']
    
    '''
    state_action = open('./state_action.txt','w')
    for state in range(len(ro_table)):
        for action in range(len(ro_table[state])):
            logical_state = stateRemapping(state)
            logical_action = actionRemapping(action)
            qrule = "ro("+logical_state+","+logical_action+","+str(int(math.floor(ro_table[state,action])))+").\n"
            state_action.write(qrule)
    state_action.close()
    import pdb
    pdb.set_trace()

    for (state,action) in ro_table_lp:
        logical_state = stateRemapping(state)
        logical_action = actionRemapping(action)
        qrule = "ro("+logical_state+","+logical_action+","+str(int(math.floor(ro_table[state,action])))+")."
        print(qrule)
    '''


    explore = True
    converged = False
    #generate_goal_file(400)
    planabandoned = False

    while episodeCount < EPISODE_LIMIT and stepCount < STEPS_LIMIT:
        print("\n\n### EPISODE "  + str(episodeCount) + "###")
        # Restart the game
        env.restart()
        episodeSteps = 0

        replanned = False
        stateaction = []
        planquality = 0
        
        #generate_rovalue_from_table(env,ro_table_lp, ro_table)


        done = False
        allsubgoallearned = True

        episodeExternalRew = 0
        
        plantrace = generateplan()


        # Run episode
        goal_index = 0
        goal_not_found = False


        # dispatch each subgoal to DQN
        # goal_index denotes the current index of action/symbolic transition to dispatch
        while not env.isTerminal() and episodeSteps <= maxStepsPerEpisode and goal_index < len(plantrace)-1 and not goal_not_found:

            goal = selectSubGoal(plantrace,goal_index)
            state_ind, action_ind = obtainStateAction(plantrace,goal_index)
            if goal == -1:
                #print "Subgoal not found for ",plantrace[goal_index+1][2]
            # now tell the planenr that don't generate such unpromising actions, by punishing with a big reward.
            # shortly we will have DQN training to rule those bad actions out.
                goal_not_found = True
            else: # goal found
                '''
                print 'current state and action:',plantrace[goal_index][2],state_ind,plantrace[goal_index][2],action_ind
                print 'predicted subgoal is: ', plantrace[goal_index+1][2],
                print 'goal explain', goalExplain[goal]
                '''

                planabandoned = False


                # train DQN for the subgoal
                while not env.isTerminal() and not env.goalReached(goal) and episodeSteps <= maxStepsPerEpisode:

                    state = env.getStackedState()
                    #action = agent_list[goal].selectMove(state, goal)
                    action = agent_list[goal].selectMove(state)
                    externalRewards = env.act(actionMap[action])

                    episodeExternalRew += externalRewards

                    stepCount += 1
                    episodeSteps += 1
                    nextState = env.getStackedState()

                if env.goalReached(goal):
                    subgoal_success_tracker[goal].append(1)
                    goalstate = plantrace[goal_index+1][2]
                    previousstate = plantrace[goal_index][2]
                    '''
                    print 'previous state',previousstate
                    print 'goal reached',goalstate
                    print 'Success times:',subgoal_success_tracker[goal].count(1)
                    '''
            #    print 'current state:', env.getStackedState()
                if obtainedKey(previousstate,goalstate):
                    print("Obtained key! Get 100 reward!")
                    reward = 100
                elif openDoor(previousstate,goalstate):
                    print("Open the door! Get 300 reward!")
                    done = True
                if goal_index == len(plantrace)-2:
                    state_next = -2
                else:
                    state_next = selectSubGoal(plantrace,goal_index+1)

                #time.sleep(60)
                if done:
                    for i in range(15):
                        env.act(3)
                    for i in range(15):
                        env.act(0)
                    break
                goal_index += 1

        planquality = calculateplanquality(ro_table,stateaction)
        print('episode rew : ', episodeExternalRew)
        print("plan quality is:", planquality)



if __name__ == "__main__":
    main()
