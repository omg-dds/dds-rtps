/// Interoperability test program for RustDDS library
use rustdds::dds::DomainParticipant;
use rustdds::dds::qos::QosPolicyBuilder;
use rustdds::dds::qos::policy::{ Reliability, Durability, History };
use rustdds::dds::data_types::DDSDuration;
use rustdds::dds::data_types::TopicKind;
use rustdds::dds::traits::TopicDescription;
use rustdds::serialization::{CDRSerializerAdapter, CDRDeserializerAdapter};
use rustdds::dds::traits::Keyed;
use serde::{Serialize, Deserialize};

use clap::{Arg, App}; // command line argument processing 
 
use mio::*; // polling 
use mio_extras::channel; // pollable channel

use log::{debug,trace};

use rand::prelude::*;

use std::time::Duration;

#[derive(Serialize,Deserialize,Clone)]
struct Shape {
	color: String,
	x: i32,
	y: i32,
	shapesize: i32,
}

impl Keyed for Shape {
	type K = String;
	fn get_key(&self) -> String {
		self.color.clone()
	}
}

const DA_WIDTH: i32 = 240;
const DA_HEIGHT: i32 = 270;

const STOP_PROGRAM: Token = Token(0);
const READER_READY: Token = Token(1);
//const WRITER_READY: Token = Token(2);

fn main() {
	log4rs::init_file("logging-config.yaml", Default::default()).unwrap();

	let matches = 
		App::new("RustDDS-interop")
        .version("0.1")
        .author("Juhana Helovuo <juhe@iki.fi>")
        .about("Command-line \"shapes\" interoperability test.")
        .arg(Arg::with_name("domain_id")
          .short("d")
          .value_name("id")
          .help("Sets the DDS domain id number")
          .takes_value(true))
        .arg(Arg::with_name("topic")
          .short("t")
          .value_name("name")
          .help("Sets the topic name")
          .takes_value(true)
      		.required(true))
        .arg(Arg::with_name("color")
          .short("c")
          .value_name("color")
          .help("Color to publish (or filter)")
          .takes_value(true))
        .arg(Arg::with_name("durability")
          .short("D")
          .value_name("durability")
          .help("Set durability")
          .takes_value(true)
          .possible_values(&["v","l", "t","p"]))
        .arg(Arg::with_name("publisher")
          .help("Act as publisher")
          .short("P")
          .conflicts_with("subscriber")
          .required_unless("subscriber"))
        .arg(Arg::with_name("subscriber")
          .help("Act as subscriber")
          .short("S")
          .conflicts_with("publisher")
          .required_unless("publisher"))
        .arg(Arg::with_name("best_effort")
          .help("BEST_EFFORT reliability")
          .short("b")
          .conflicts_with("reliable"))
        .arg(Arg::with_name("reliable")
          .help("RELIABLE reliability")
          .short("r")
          .conflicts_with("best_effort"))
        .arg(Arg::with_name("history_depth")
          .help("Keep history depth")
          .short("k")
          .takes_value(true)
          .value_name("depth"))
        .get_matches();

  // Gets a value for config if supplied by user, or defaults to "default.conf"
  let topic_name = matches.value_of("topic").unwrap_or("shapes");
  let domain_id  = matches.value_of("domain_id")
  									.unwrap_or("0")
  									.parse::<u16>()
  									.unwrap_or(0);
  let color = matches.value_of("color").unwrap_or("BLUE");

  let domain_participant = DomainParticipant::new(domain_id);

  let qos = QosPolicyBuilder::new()
  		.reliability(
	  			if matches.is_present("reliable") {	
	  				Reliability::Reliable { max_blocking_time: DDSDuration::DURATION_ZERO } 
					} else {
						Reliability::BestEffort
					}
  			)
  		.durability(
	  			match matches.value_of("durability") {
	  				Some("v") => Durability::Volatile,
	  				Some("l") => Durability::TransientLocal,
	  				Some("t") => Durability::Transient,
	  				Some("p") => Durability::Persistent,
	  				_ => Durability::Volatile,	  				
	  			}
  			)
  		.history(
  				match matches.value_of("history_depth").map( |d| d.parse::<i32>() )  {
  					None | 
  					Some(Err(_)) => History::KeepAll,
  					Some(Ok(d)) =>
  						if d < 0 { History::KeepAll } else { History::KeepLast{ depth: d } },

  				}
  			)
  		.build();

  let topic = domain_participant
  	.create_topic(topic_name, "ShapeType", &qos, TopicKind::WithKey)
  	.unwrap();
	println!("Topic name is {}", topic.get_name());

  // Set Ctrl-C handler
  let (stop_sender,stop_receiver) = channel::channel();
  ctrlc::set_handler(move || {
        stop_sender.send( () ).unwrap_or( () )
        // ignore errors, as we are quitting anyway
    }).expect("Error setting Ctrl-C handler");
	println!("Press Ctrl-C to quit.");

	let poll = Poll::new().unwrap();
	let mut events = Events::with_capacity(4);

	poll.register(&stop_receiver, STOP_PROGRAM, Ready::readable(),PollOpt::edge())
  		.unwrap();

  if matches.is_present("publisher") {
  	debug!("Publisher");
  	let publisher = domain_participant.create_publisher(&qos).unwrap();
  	let writer = publisher
  				.create_datawriter::<Shape, CDRSerializerAdapter<Shape>>(
				    None,
				    topic,
				    None)
				  .unwrap();
    let mut shape_sample = Shape { color: color.to_string(), x: 0, y: 0, shapesize: 21 };
    let mut random_gen = thread_rng();
    // a bit complicated lottery to ensure we do not end up with zero velocity.
    let mut x_vel = if random() { random_gen.gen_range(1..5) } else { random_gen.gen_range(-5..-1) };
    let mut y_vel = if random() { random_gen.gen_range(1..5) } else { random_gen.gen_range(-5..-1) };
  	loop {
  		poll
  			.poll(&mut events, Some(Duration::from_millis(500)))
  			.unwrap();
  		for event in &events {
  			match event.token() {
  				STOP_PROGRAM => {
  					match stop_receiver.try_recv() {
  						Ok(_) => {
		  					println!("Done.");
		  					return  							
  						}
  						Err(_) => { /* Can this even happen? */ }
  					}
  				}
  				other_token => {
  					println!("Polled event is {:?}. WTF?", other_token);
					}
  			}
  		}

      let r = move_shape(shape_sample,x_vel,y_vel);     
      shape_sample = r.0;
      x_vel = r.1;
      y_vel = r.2;

      // write to DDS
      trace!("Writing shape color {}", &color);
  		writer.write( shape_sample.clone() , None)
  			.expect("DataWriter write failed.")
  	} // loop
  } else  if matches.is_present("subscriber") {
  	debug!("Subscriber");
  	let subscriber = domain_participant.create_subscriber(&qos).unwrap();
  	let mut reader = subscriber
  		.create_datareader::<Shape, CDRDeserializerAdapter<Shape>>(
    			topic.clone(),
    			None, // entity id
    			None, // get qos policy from subscriber
    		)
  		.unwrap();
  	poll.register(&reader, READER_READY, Ready::readable(),PollOpt::edge())
  		.unwrap();
  	debug!("Created DataReader");
  	loop {
  		poll.poll(&mut events, None).unwrap();
  		for event in &events {
  			match event.token() {
  				STOP_PROGRAM => {
  					match stop_receiver.try_recv() {
  						Ok(_) => {
		  					println!("Done.");
		  					return  							
  						}
  						Err(_) => { /* Can this even happen? */ }
  					}
  				}
  				READER_READY => {
  					loop {
  						trace!("DataReader triggered");
	  					match reader.take_next_sample() {
	  						Ok(Some(sample)) =>
	  							match sample.into_value() {
	  								Ok(sample) =>	  							 
			  							println!("{:10.10} {:10.10} {:3.3} {:3.3} [{}]",
								  							topic.get_name(), 
								  							sample.color,
								  							sample.x,
								  							sample.y,
								  							sample.shapesize, 
									  						),
			  						Err(key) =>
			  							println!("Disposed key {:?}", key),
			  						},
	  						Ok(None) => break, // no more data
	  						Err(e) => println!("DataReader error {:?}", e),
	  					} // match
	  				} 
  				}
  				other_token => {
  					println!("Polled event is {:?}. WTF?", other_token);
  				}
  			} // match
    	} // for
  	} // loop
  } else {
  	println!("Nothing to do.");
  }

}

fn move_shape(shape:Shape, xv:i32, yv:i32) -> (Shape,i32,i32) {
  let half_size = shape.shapesize/2 + 1;
  let mut x = shape.x + xv;
  let mut y = shape.y + yv;

  let mut xv_new = xv;
  let mut yv_new = yv;

  if x < half_size {
    x = half_size;
    xv_new = -xv;
  }
  if x > DA_WIDTH - half_size {
    x = DA_WIDTH - half_size;
    xv_new = -xv;
  }
  if y < half_size {
    y = half_size;
    yv_new = -yv;
  }
  if y > DA_HEIGHT - half_size {
    y = DA_HEIGHT - half_size;
    yv_new = -yv;
  }
  ( Shape { color: shape.color, x, y, shapesize: shape.shapesize } , xv_new , yv_new)
}