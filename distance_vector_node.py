from simulator.node import Node
import json
import sys

class DV_Entry:
    def __init__(self, dest, dist, path, seq_num):
        self.dest = dest
        self.dist = dist
        self.path = path
        self.seq_num = seq_num  # I need to figure what to do for this


class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.forwarding_table = {}
        self.neighbors_latency = {}

    # Return a string
    def __str__(self):
        return "Rewrite this function to define your node dump printout"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        send_update = False

        # latency = -1 if delete a link
        if latency == -1:
            # Return if the link never existed
            if neighbor not in self.neighbors_latency:
                return

            # "Remove" path to neighbor
            self.neighbors_latency[neighbor] = sys.maxsize

            # Check for all paths that contain that neighbor
            for key, entry in self.forwarding_table.items():
                if entry.path[0] == neighbor:
                    # "Remove" path because we can no longer get there
                    self.forwarding_table[key].dist = sys.maxsize
                    send_update = True
        # Distance has changed!
        else:
            # Get change in latency
            latency_diff = latency - self.neighbors_latency.get(neighbor, 0)
            # Update neighbor latency
            self.neighbors_latency[neighbor] = latency

            # Check every node to see if we need to update them
            for key, entry in self.forwarding_table.items():
                # Update path to neighbor if closer
                if key == neighbor and latency < entry.dist:
                    entry.dist = latency
                    entry.path = [neighbor]
                    send_update = True
                # Update paths containing the link
                elif entry.path[0] == neighbor:
                    entry.dist += latency_diff
                    send_update = True

            # Check if we have no path to neighbor
            if neighbor not in self.forwarding_table:
                # Add the path
                self.forwarding_table[neighbor] = DV_Entry(neighbor, latency, [neighbor], 0)
                send_update = True
        # Send updated DV
        if send_update:
            self.send_to_neighbors(self._get_dv_json())

    # Fill in this function
    def process_incoming_routing_message(self, m):
        send_update = False
        help_neighbor = False
        neighbor_table = json.loads(m)
        neighbor = neighbor_table[0]['path'][0]
        for entry in neighbor_table:
            e_dest = entry['dest']
            e_dist = entry['dist']
            e_path = entry['path']

            # Check if path includes up AKA a loop
            if self.id in e_path:
                continue

            new_dist = min(e_dist + self.neighbors_latency[neighbor], sys.maxsize)
            # Check if we don't have the path
            if self.forwarding_table.get(e_dest, -1) == -1:
                # Add the path
                self.forwarding_table[e_dest] = DV_Entry(e_dest, new_dist, e_path, 0)
                send_update = True

            # Check if that path is shorter
            elif new_dist < self.forwarding_table[e_dest].dist or (e_path == self.forwarding_table[e_dest].path and new_dist > self.forwarding_table[e_dest].dist):
                # Update the path
                self.forwarding_table[e_dest].dist = new_dist
                self.forwarding_table[e_dest].path = e_path
                send_update = True

            # Check if our local path is better
            if e_dest in self.neighbors_latency.keys() and self.neighbors_latency[e_dest] < self.forwarding_table[e_dest].dist:
                # Change to local path
                self.forwarding_table[e_dest].dist = new_dist
                self.forwarding_table[e_dest].path = e_path
                send_update = True

            # Check if we can help out neighbor
            if e_dist > self.forwarding_table[e_dest].dist + self.neighbors_latency[neighbor]:
                help_neighbor = True
        if send_update:
            self.send_to_neighbors(self._get_dv_json())
        elif help_neighbor:
            self.send_to_neighbor(neighbor, self._get_dv_json())

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if self.forwarding_table.get(destination, sys.maxsize) != sys.maxsize:
            return self.forwarding_table[destination].path[0]
        return -1

    def _get_dv_json(self) -> str:
        # JSON I should have
        # List of:
        # Dest, Dist, [Me + Path]
        obj = []
        for key, value in self.forwarding_table.items():
            temp = {}
            temp['dest'] = value.dest
            temp['dist'] = value.dist
            temp['path'] = [self.id] + value.path
            obj.append(temp)
        #print(f"{self.id} Forwarding Table:")
        #print(json.dumps(obj))
        return json.dumps(obj)
