import copy

from simulator.node import Node
import json
import sys

INF = sys.maxsize

class DV_Entry:
    def __init__(self, dest, dist, path, seq_num):
        self.dest = dest
        self.dist = dist
        self.path = path
        self.seq_num = seq_num  # I need to figure what to do for this


class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        # Initialize neighbors and the forwarding table
        self.forwarding_table = {}
        self.forwarding_table[id] = DV_Entry(id, 0, [], 0)
        self.neighbors_latency = {}
        self.neighbors_latency[id] = 0

    # Return a string
    def __str__(self):
        return "Rewrite this function to define your node dump printout"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        send_update = False

        # Check if the link was deleted (AKA latency == -1)
        if latency == -1:
            # Check that the link did exist before
            if neighbor not in self.neighbors_latency.keys():
                # The link didn't exist
                return

            # Delete the link
            del self.neighbors_latency[neighbor]

            # Change every path that used the link
            for key, entry in self.forwarding_table.items():
                if entry.dest == self.id:
                    continue
                # Check if first step is to neighbor
                if entry.path[0] == neighbor:
                    # Delete path
                    entry.dist = INF
                    entry.path = [None]
                    send_update = True

        # We are changing the link dist!
        else:
            # Get change in latency
            latency_diff = latency - self.neighbors_latency.get(neighbor, 0)
            # Update neighbor latency
            self.neighbors_latency[neighbor] = latency
            # Check every path that uses the link and update it:
            for key, entry in self.forwarding_table.items():
                if entry.dest == self.id:
                    continue
                if entry.path[0] == neighbor:
                    entry.dist += latency_diff
                    send_update = True
            # Check if the link is new
            if neighbor not in self.forwarding_table:
                self.forwarding_table[neighbor] = DV_Entry(neighbor, latency_diff, [neighbor], -1)
                send_update = True
            # Check all paths to neighbors and see if direct links are better
            for dest, latency in self.neighbors_latency.items():
                if latency < self.forwarding_table[dest].dist:
                    self.forwarding_table[dest].dist = latency
                    self.forwarding_table[dest].path = [dest]
                    send_update = True

        # Send updated DV
        if send_update:
            self._update_neighbors()

    # Fill in this function
    def process_incoming_routing_message(self, m):
        send_update = False
        help_neighbor = False
        neighbor_list = json.loads(m)
        neighbor = neighbor_list[0]  # First entry will be neighbor ID
        # Loop through every entry in the neighbor list
        for lst in neighbor_list[1:]:
            entry = DV_Entry(lst[0], lst[1], lst[2], lst[3])
            # Check if they are trying to sell us us
            if self.id == entry.dest:
                continue
            # Check if there is a loop
            if self.id in entry.path:
                continue
            # Check if the entry is new
            if entry.dest not in self.forwarding_table:
                self.forwarding_table[entry.dest] = copy.copy(entry)
                send_update = True
            # Check we use the path
            elif neighbor == self.forwarding_table[entry.dest].path[0]:
                # Check if has been no change in the path
                if entry.dist == self.forwarding_table[entry.dest].dist and entry.path == self.forwarding_table[entry.dest].path:
                    continue
                # There has been a change! Update it
                self.forwarding_table[entry.dest] = entry
                send_update = True
            # Check if the entry is better than our current one
            elif entry.dist < self.forwarding_table[entry.dest].dist:
                self.forwarding_table[entry.dest] = entry
                send_update = True
            # Check if they need help
            elif entry.dist > self.forwarding_table[entry.dest].dist + 2 * self.neighbors_latency.get(neighbor, INF // 2 - 1):
                help_neighbor = True
        # Check all paths to neighbors and see if direct links are better
        for dest, latency in self.neighbors_latency.items():
            if latency < self.forwarding_table[dest].dist:
                self.forwarding_table[dest].dist = latency
                self.forwarding_table[dest].path = [dest]
                send_update = True
        if send_update:
            self._update_neighbors()
        elif help_neighbor:
            self._update_neighbor(neighbor)

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if self.forwarding_table.get(destination, INF) != INF:
            return self.forwarding_table[destination].path[0]
        return -1

    def _update_neighbors(self):
        for neighbor in self.neighbors_latency.keys():
            self._update_neighbor(neighbor)

    def _update_neighbor(self, neighbor):
        # Get base list to send
        latency = self.neighbors_latency.get(neighbor, -1)
        if latency == -1:
            return
        obj = [self.id]
        for key, value in self.forwarding_table.items():
            if value.path != [None]:
                obj.append([value.dest, value.dist + latency, [self.id] + value.path, -1])
            else:
                obj.append([value.dest, INF, [None], -1])
        #print(json.dumps(obj))
        self.send_to_neighbor(neighbor, json.dumps(obj))

