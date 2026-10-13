"""Source script for the built-in sample episode ("Wired Planet, episode 12").

`scripts/make_samples.py` turns this into every supported input format (pasted text, .txt,
.md, .srt, .vtt and seven audio formats) with timestamps that match the generated audio.
Facts are kept general and well established so the quiz can be checked by a human.
"""

TITLE = "Wired Planet, Episode 12: How the Internet Actually Reaches You"
SHOW = "Wired Planet"

# (speaker, paragraph). Each paragraph is split into sentences for subtitle cues.
SCRIPT = [
    # --- intro
    ("Nadia", "Welcome to Wired Planet, the show about the hidden machinery behind everyday technology. I'm Nadia."),
    ("Omar", "And I'm Omar. Today we're following a single web page from a server on the other side of the world all the way to your phone. Nadia, when most people picture the internet, what do they picture?"),
    ("Nadia", "Usually something in the sky. Satellites, or a vague cloud. But the honest answer is that the internet is mostly glass and copper lying on the ground and on the sea floor. The cloud is really a lot of buildings full of computers, joined together by cables."),
    ("Omar", "So let's start at the bottom of the ocean. How much international traffic actually goes through undersea cables?"),
    ("Nadia", "The vast majority. Industry estimates usually say well over ninety five percent of data travelling between continents goes through submarine fibre optic cables. Satellites carry a small share, and they matter a lot for remote places and ships, but cables carry the bulk because they offer far more capacity at lower cost."),
    # --- history
    ("Omar", "These cables are not a new idea, right?"),
    ("Nadia", "Not at all. The first transatlantic telegraph cable was completed in 1858. Queen Victoria sent a message to the American president, and people celebrated in the streets. Then the cable failed after about three weeks. Engineers had pushed too much voltage through it, and the insulation broke down."),
    ("Omar", "Three weeks. That's a rough launch."),
    ("Nadia", "It is, but it taught a lasting lesson. A cable on the sea floor has to survive for decades with almost no maintenance, so it has to be designed carefully and treated gently. Modern cables are expected to last around twenty five years."),
    # --- how fibre works
    ("Omar", "What does a modern cable look like? I imagine something as thick as a tree trunk."),
    ("Nadia", "In the deep ocean, a typical cable is about as thick as a garden hose. At its heart are a few hair thin strands of glass fibre. Around them are layers of steel wire for strength, copper to carry electrical power, and plastic for insulation. Near the shore, where ships and fishing gear are a bigger risk, the cable gets extra armour and is often buried under the sea bed."),
    ("Omar", "Why does a cable need electrical power if it is carrying light?"),
    ("Nadia", "Because light fades as it travels through glass. Every so often along the cable there is a repeater, which boosts the signal so it can keep going. Those repeaters need power, and that power is fed in from stations on land at each end."),
    ("Omar", "And the data itself is just pulses of light?"),
    ("Nadia", "Yes. A laser switches on and off, or changes its pattern, billions of times per second, and each change encodes information. Engineers also send many colours of light down the same fibre at once, and each colour carries its own stream of data. That trick is called wavelength division multiplexing, and it is why a single fibre can carry an enormous amount of traffic."),
    ("Omar", "How fast does that light move?"),
    ("Nadia", "Inside glass, light travels at roughly two thirds of its speed in a vacuum, so about two hundred thousand kilometres per second. That sounds instant, but over long distances it adds up. A signal crossing the Atlantic between London and New York needs a few tens of milliseconds each way, just because of distance. No amount of clever software can beat that physical limit."),
    # --- packets
    ("Omar", "Okay, so we have this giant glass highway. But a web page isn't one big lump of light. How does it actually travel?"),
    ("Nadia", "It gets chopped into small pieces called packets. Each packet carries a slice of the data plus a label saying where it came from and where it is going. Packets from the same page can take different routes and arrive out of order, and your device puts them back together."),
    ("Omar", "Who decided it should work that way?"),
    ("Nadia", "The core rules come from a design described by Vint Cerf and Bob Kahn in 1974, which became the TCP and IP protocols. IP is the addressing system, a bit like the address on an envelope. TCP is the part that makes delivery reliable. Your device acknowledges the packets it receives, and if one goes missing, the sender notices and sends it again."),
    ("Omar", "So when a video call gets choppy, is that packets going missing?"),
    ("Nadia", "Often, yes. For live calls, waiting for a lost packet to be resent would cause an awkward pause, so real time apps usually accept a little loss and keep going. That is why you might see a frozen frame or hear a robotic voice for a moment, rather than the call stopping completely."),
    # --- DNS
    ("Omar", "Let's go back to the start of the journey. I type a website name into my browser. What happens first?"),
    ("Nadia", "Your device has to turn that name into a numeric address, because the network routes packets using numbers, not words. That job belongs to the Domain Name System, usually called DNS. It was introduced in 1983, and before that, computers relied on a single shared list of names and addresses that had to be copied around by hand."),
    ("Omar", "A single list for the whole internet? That can't have scaled."),
    ("Nadia", "It didn't. DNS replaced it with a hierarchy. There are root servers at the top, then servers responsible for endings like dot com or dot org, and then servers run by each organisation for its own names. Your device usually asks a nearby resolver, often run by your internet provider, and that resolver walks down the hierarchy and remembers the answer for a while so the next lookup is faster."),
    ("Omar", "So the phone book is spread out across the whole world."),
    ("Nadia", "Exactly. And because answers are remembered, or cached, most lookups never need to travel very far."),
    # --- routing / BGP
    ("Omar", "Once my device knows the address, how do the packets find their way across all these different networks?"),
    ("Nadia", "The internet is really a network of networks. Internet providers, universities, cloud companies and many others each run their own network. They tell each other which addresses they can reach using a protocol called the Border Gateway Protocol, or BGP. Each network then picks a path for traffic based on those announcements and on its business agreements."),
    ("Omar", "That sounds like it depends a lot on trust."),
    ("Nadia", "It does, and that is one of its weak points. In 2008, a provider in Pakistan tried to block YouTube inside the country. It announced a route for YouTube's addresses, and that announcement leaked out to the wider internet. For a couple of hours, a large share of the world's YouTube traffic was pulled toward the wrong network and simply disappeared."),
    ("Omar", "One mistake in one country, and the whole world notices."),
    ("Nadia", "That is the trade off. BGP is flexible and lets the network route around failures, but it was built in an era when operators mostly trusted each other. Today there are newer security measures that let networks check whether an announcement is legitimate, and adoption has been growing steadily."),
    # --- CDNs
    ("Omar", "Here's something I've wondered about. If light needs time to cross the ocean, why does a popular website from another continent still load quickly?"),
    ("Nadia", "Because very often the page isn't coming from the other continent at all. Large websites use content delivery networks, which keep copies of popular files on servers in many cities. When you ask for a video or an image, you are usually sent to a nearby copy. The original server might be far away, but the copy could be in your own city."),
    ("Omar", "So the fastest way to send data a long way is to not send it a long way."),
    ("Nadia", "That's a good way to put it. Caching close to the user saves time, and it also saves expensive long distance capacity for the traffic that really needs it."),
    # --- the last mile
    ("Omar", "Then there's the last step, from the street to my phone."),
    ("Nadia", "Right. That last stretch might be fibre to your building, an older copper line, a cable television line, or a mobile network. If you are on wifi at home, the final few metres are radio waves between your router and your phone. Ironically, that short wireless hop is often the slowest and least reliable part of the whole journey."),
    ("Omar", "So when my video buffers, I should blame the wall between me and the router before I blame the ocean."),
    ("Nadia", "Quite often, yes. Moving closer to the router, or using a cable, fixes a surprising number of problems."),
    # --- cable faults and repair
    ("Omar", "Let's talk about things going wrong. What actually breaks undersea cables? I've heard sharks bite them."),
    ("Nadia", "Sharks have bitten cables, and there are photos to prove it, but they are a tiny part of the problem. Most faults are accidents caused by people, especially fishing gear dragged along the sea bed and ships dropping anchor in the wrong place. Natural events like earthquakes and underwater landslides cause some of the rest."),
    ("Omar", "And how do you fix a cable that's lying thousands of metres down?"),
    ("Nadia", "With a specialised repair ship. The crew works out roughly where the fault is by sending test signals down the cable from shore. Then the ship lowers a hook called a grapnel, catches the cable, and lifts the damaged section to the surface. Technicians splice in a new piece on board, a very delicate job with glass fibres, and lower it back down. A repair can take days or weeks, depending on the weather and how deep the cable is."),
    ("Omar", "Does the internet go down while that happens?"),
    ("Nadia", "Usually not, because important routes have several cables, and traffic is shifted onto the others. The problem is when a region depends on only one or two cables. Then a single fault can slow the connection for a whole country, which is why many governments now push for more routes and more landing points."),
    # --- wrap up
    ("Omar", "Let's sum up for anyone who wants to remember the journey."),
    ("Nadia", "Sure. First, your device uses DNS to turn a name into a numeric address. Second, the page is split into packets, and TCP makes sure they all arrive. Third, networks use BGP to choose a path between them. Fourth, the long distances are covered by fibre optic cables, mostly on the sea floor, where light carries the data. And finally, a content delivery network often means the data didn't have to travel very far in the first place."),
    ("Omar", "And the practical tip?"),
    ("Nadia", "If things feel slow, check the short hops first. Your wifi signal and your local connection are much more likely to be the bottleneck than the ocean."),
    ("Omar", "That's all for this episode of Wired Planet. Thanks for listening, and next time we'll look at how data centres keep millions of computers cool."),
]
