import json

from simulator.node import Node
class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.links = {}  # Dictionary of frozenset: dist
        self.link_seq_nums = {}
        self.neighbors = set()


    # Return a string
    def __str__(self):
        return "Rewrite this function to define your node dump printout"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        # latency = -1 if delete a link: We will represent these as -1 for now

        # Get the link
        link = frozenset([self.id, neighbor])

        # Increase seq_num
        seq_num = self.link_seq_nums.get(link, 0) + 1
        self.link_seq_nums[link] = seq_num

        # Update the latency
        self.links[link] = latency
        # Check if the link is not being deleted
        if latency != -1:
            self.neighbors.add(neighbor)

        # Send update to neighbors
        for n in self.neighbors:
            if n != neighbor:
                self.send_to_neighbor(n, json.dumps([self.id, link, latency, seq_num]))

    # Fill in this function
    def process_incoming_routing_message(self, m):
        # Load the message
        neighbor, link, latency, seq_num = json.loads(m)

        # Check if the seq_num is new or the link is new
        if link not in self.links.keys() or seq_num > self.link_seq_nums[link]:
            # Update our link
            self.links[link] = latency
            self.link_seq_nums[link] = seq_num
            # Send message to all our neighbors
            for n in self.neighbors:
                if n != neighbor:
                    self.send_to_neighbor(n, json.dumps([self.id, link, latency, seq_num]))
        # Check if the link is worse
        elif seq_num < self.link_seq_nums[link]:
            # Send a message back to the neighbor
            self.send_to_neighbor(neighbor, json.dumps([self.id, link, self.links[link], self.link_seq_nums[link]]))
        # If neither of these are teh case, we ignore the message

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        return -1
